# app/routes.py
from flask import Blueprint, jsonify, request, render_template
from datetime import datetime 
import json

from database import insert_event, get_recent_events
from app.processing import (
    validate_event,
    normalize_event,
    build_features,
)
from app.model import evaluate_event  # IsolationForest أو أي نموذج AI عندك

main_bp = Blueprint("main", __name__)


# ---------------- health check ----------------
@main_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "SND risk engine is running"
    })


# ------------- صفحة الداشبورد ---------------
@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """
    تعرض ملف dashboard.html من مجلد templates/
    """
    return render_template("dashboard.html")


# ------------- API: آخر الأحداث كـ JSON ---------------
@main_bp.route("/events", methods=["GET"])
def events():
    """
    إرجاع آخر N أحداث بصيغة JSON لاستخدامها في الداشبورد.
    """
    rows = get_recent_events(limit=50)

    clean_events = []
    for r in rows:
        # متوافق مع أغلب إصدارات events.db التي استخدمناها سابقاً:
        # id, user_id, device, city, service, event_time, risk_score, decision
        clean_events.append({
            "id": r[0],
            "user_id": r[1],
            "device": r[2],
            "city": r[3],
            "region": r[4],
            "os": r[5],
            "browser": r[6],
            "service": r[7],
            "event_time": r[8],
            "risk_score": r[9],
            "decision": r[12],
        })

    return jsonify({"events": clean_events})


# ------------- دالة مساعدة لحساب rules_score ---------------
def compute_rules_score(features: dict) -> float:
    """
    قواعد تقييم إضافية مبنية على السلوك:
    - مدينة جديدة / جهاز جديد / خدمة حساسة / وقت متأخر / سبايك في النشاط...
    ترجع قيمة بين 0 و 100 تقريباً.
    """

    rules_score = 0.0

    is_known_city = features.get("is_known_city", 0)
    is_new_device = features.get("is_new_device", 0)
    is_sensitive_service = features.get("is_sensitive_service", 0)
    events_last_1h = features.get("events_last_1h", 0)
    events_last_24h = features.get("events_last_24h", 0)
    time_window = features.get("time_window", "unknown")
    avg_daily_events = features.get("avg_daily_events", 0.0)

    # مدينة غير مألوفة للمستخدم
    if not is_known_city:
        rules_score += 20.0

    # جهاز جديد
    if is_new_device:
        rules_score += 20.0

    # خدمة حساسة (تغيير جوال / إعادة تعيين كلمة مرور ...)
    if is_sensitive_service:
        rules_score += 30.0

    # وقت استخدام غريب (ليل / فجر)
    if time_window in ["night", "late_night"]:
        rules_score += 10.0

    # نشاط عالي جداً في آخر ساعة / 24 ساعة (Spike)
    if events_last_1h >= 5 or events_last_24h >= 20:
        rules_score += 10.0

    # معدل استخدام يومي غير طبيعي
    if avg_daily_events > 50:
        rules_score += 10.0

    # حصر القيم بين 0 و 100
    return max(0.0, min(100.0, rules_score))


# ------------- API: دالة التقييم الرئيسية /score ---------------
@main_bp.route("/score", methods=["POST"])
def score():
    """
    نقطة الدخول الأساسية:
    - تستقبل حدث سلوكي من خدمة خارجية
    - تتحقق من صحة البيانات
    - تنظّف الحدث وتطبّع المدن/الأجهزة
    - تبني ميزات سلوكية (Features)
    - تمرر الميزات لنموذج الذكاء الاصطناعي (IsolationForest)
    - تحسب ai_risk_score + rules_score + risk_score النهائي
    - تطبق طبقة القرار Decision Layer (Allow / Alert / Challenge / Block)
    - تحفظ الحدث منخفض المخاطر في قاعدة البيانات لبناء البصمة السلوكية
    """

    # -------- 1) استلام البيانات والتحقق --------
    data = request.get_json() or {}

    valid, message = validate_event(data)
    if not valid:
        return jsonify({"error": message}), 400

    # -------- 2) التطبيع / التنظيف --------
    # normalize_event قد يضيف حقول داخلية مثل:
    #  _event_dt (datetime)
    #  _timestamp_ms (int)
    cleaned = normalize_event(data)

    # -------- 3) بناء الميزات السلوكية --------
    features = build_features(cleaned)

    # -------- 4) استدعاء نموذج الذكاء الاصطناعي --------
    # نفترض أن evaluate_event يرجع raw_score في المدى [-0.5, +0.5]
    raw_score = evaluate_event(features)

    # نحول raw_score إلى ai_risk_score بين 0 و 100
    clamped = max(-0.5, min(0.5, raw_score))
    anomaly_score = (0.5 - clamped) / 1.0
    ai_risk_score = anomaly_score * 100.0

    # -------- 5) حساب rules_score --------
    rules_score = compute_rules_score(features)

    # -------- 6) دمج الذكاء مع القواعد --------
    # وزن الذكاء 55% والقواعد 45% كما اختبرنا سابقاً
    risk_score = (0.55 * ai_risk_score) + (0.45 * rules_score)

    # -------- 7) طبقة قرار خاصة بالمستخدم الجديد (Warm Start) --------
    # -------- 7 + 8) Decision Layer (baseline + warm start + challenge) --------

    # 1) القرار الأساسي حسب risk_score
    if risk_score <= 30:
        decision = "Allow"
    elif risk_score <= 60:
        decision = "Alert"
    elif risk_score <= 80:
        decision = "Challenge"
    else:
        decision = "Block"

    # 2) منطق المستخدم الجديد (Warm Start) + منع تسميم البصمة
    is_new_user = features.get("is_new_user", 0)
    city_freq = features.get("city_frequency", 0.0)
    device_freq = features.get("device_frequency", 0.0)
    service_freq = features.get("service_frequency", 0.0)

    if is_new_user:
        # مستخدم جديد وكل شيء طبيعي (مدينة + جهاز + خدمة متكررة) → سماح محافظ
        if (
            city_freq == 1.0
            and device_freq == 1.0
            and service_freq == 1.0
            and risk_score <= 60
        ):
            decision = "Allow"
            # نجبر السكور أن يكون منخفض عشان نبني baseline نظيفة
            risk_score = min(risk_score, 25.0)
        else:
            # مستخدم جديد لكن السلوك مو مثالي → نرفعه إلى Alert محافظ
            if risk_score < 60:
                decision = "Alert"
                risk_score = min(risk_score, 60.0)


    # 3) خدمات حساسة: بين 61–80 نفضّل Challenge بدل Alert
    is_sensitive_service = features.get("is_sensitive_service", 0)
    if is_sensitive_service and 61 <= risk_score <= 80:
        decision = "Challenge"

    # 4) تشديد إضافي للخدمات الحساسة إذا السكور >= 40
    if is_sensitive_service and risk_score >= 40:
        decision = "Challenge"

    # 5) Spike قوي جداً في الساعة / اليوم
    events_last_1h = features.get("events_last_1h", 0)
    events_last_24h = features.get("events_last_24h", 0)

    # أرقام أكثر واقعية لاستخدام منصة حكومية واحدة
    # - أكثر من 20 حدث في ساعة واحدة
    # - أو أكثر من 80 حدث في يوم واحد
    if events_last_1h >= 5 or events_last_24h >= 24:
        # نرفع السكور لحد أدنى 60 (منطقة Challenge)
        if risk_score < 60:
            risk_score = 60.0
        decision = "Challenge"


    # -------- 9) تجهيز payload خام للتخزين (حذف الحقول المؤقتة) --------
    payload_for_store = dict(cleaned)

    # نحذف الحقول الداخلية التي لا نريدها في raw_payload
    payload_for_store.pop("_event_dt", None)
    payload_for_store.pop("_timestamp_ms", None)

    # تأكد أن event_time عبارة عن نص ISO قبل التخزين
    if isinstance(payload_for_store.get("event_time"), datetime):
        payload_for_store["event_time"] = payload_for_store["event_time"].isoformat()

    raw_payload = json.dumps(payload_for_store, ensure_ascii=False)

    # -------- 10) حفظ الحدث في قاعدة البيانات --------
    insert_event(
        user_id=payload_for_store["user_id"],
        device=payload_for_store["device"],
        city=payload_for_store["city"],
        service=payload_for_store["service"],
        event_time=payload_for_store["event_time"],
        region=payload_for_store.get("region", ""),
        os_name=payload_for_store.get("os", ""),
        browser=payload_for_store.get("browser", ""),
        timestamp_ms=int(
            datetime.fromisoformat(payload_for_store["event_time"]).timestamp() * 1000
        ),
        ai_risk_score=ai_risk_score,
        rules_score=rules_score,
        risk_score=risk_score,
        decision=decision,
        raw_payload=raw_payload,
    )

    # -------- 11) تجهيز الرد للعميل --------
    response = {
        "risk_score": risk_score,
        "ai_risk_score": ai_risk_score,

        "rules_score": rules_score,
        "decision": decision,
        "raw_score": raw_score,
        "features_used": features,
        "received_payload": payload_for_store,
    }
    return jsonify(response), 200
