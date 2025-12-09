import os
import sqlite3
from datetime import datetime
from typing import Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

from app.processing import build_features

MODEL_PATH = "snd_model.pkl"

# نفس المفاتيح الراجعة من build_features
FEATURE_KEYS: List[str] = [
    # زمنية
    "event_hour",
    "day_of_week",
    "is_weekend",
    "is_night",
    # كثافة الاستخدام
    "events_last_1h",
    "events_last_24h",
    "avg_daily_events",
    "minutes_since_last_event",
    # بصمة المستخدم
    "is_known_city",
    "is_new_device",
    "is_sensitive_service",
    "city_frequency",
    "device_frequency",
    "service_frequency",
]

_model = None  # يتم تحميله عند أول استخدام


def _vector_from_features(features: Dict[str, float]) -> np.ndarray:
    """
    تحويل قاموس الميزات إلى vector رقمي بنفس ترتيب FEATURE_KEYS.
    أي ميزة ناقصة نضع لها 0.
    """
    return np.array([[float(features.get(k, 0.0)) for k in FEATURE_KEYS]], dtype=float)


def train_model(
    db_path: str = "events.db",
    model_path: str = MODEL_PATH,
    random_state: int = 42,
) -> None:
    """
    تدريب IsolationForest على الأحداث المخزّنة في قاعدة البيانات
    باستخدام build_features لكل حدث، ثم حفظ النموذج إلى ملف.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # نأخذ الأحداث الأساسية لبناء الميزات
    cur.execute(
        """
        SELECT user_id, device, city, service, event_time
        FROM events
        ORDER BY datetime(event_time) ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("[train_model] لا توجد أحداث في قاعدة البيانات للتدريب.")
        # ممكن مستقبلاً نولّد بيانات تدريب صناعية هنا
        return

    X = []
    for (user_id, device, city, service, event_time) in rows:
        data = {
            "user_id": user_id,
            "device": device,
            "city": city,
            "service": service,
            "event_time": event_time,
        }
        try:
            feats = build_features(data)
            vec = [float(feats.get(k, 0.0)) for k in FEATURE_KEYS]
            X.append(vec)
        except Exception as e:
            # نتجاهل أي سطر فيه مشكلة ميزات
            print(f"[train_model] تخطي حدث بسبب خطأ في الميزات: {e}")

    if not X:
        print("[train_model] لم نستطع توليد ميزات كافية للتدريب.")
        return

    X = np.array(X, dtype=float)

    # نموذج IsolationForest للكشف عن الشذوذ
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,  # يفترض أن 5% فقط شاذ
        random_state=random_state,
    )
    model.fit(X)

    joblib.dump(model, model_path)
    print(f"[train_model] تم تدريب النموذج وحفظه في: {model_path}")
    print(f"[train_model] عدد العينات المستخدمة في التدريب: {X.shape[0]}")


def _load_model() -> IsolationForest:
    """
    تحميل النموذج من الملف، أو إعادة استخدامه لو كان محمّل مسبقاً.
    """
    global _model

    if _model is not None:
        return _model

    if not os.path.exists(MODEL_PATH):
        print("[model] ملف النموذج غير موجود، يُفضّل تشغيل train_model أولاً.")
        # في حالة عدم وجود نموذج، ننشئ واحداً بسيطاً افتراضياً لتجنب الانهيار
        dummy = IsolationForest(
            n_estimators=50,
            contamination=0.1,
            random_state=42,
        )
        # تدريب سريع على نقطة واحدة (صحيّة) حتى لا يرمي خطأ
        dummy.fit(np.zeros((10, len(FEATURE_KEYS))))
        _model = dummy
        return _model

    _model = joblib.load(MODEL_PATH)
    print("[model] تم تحميل النموذج من القرص.")
    return _model


def evaluate_event(features: Dict[str, float]) -> float:
    """
    استقبال الميزات السلوكية لقضية واحدة،
    وتحويلها إلى vector، ثم حساب درجة الشذوذ من النموذج.

    نستخدم decision_function:
    - قيم أعلى (قريبة من 0.5) = طبيعي
    - قيم أقل (قريبة من -0.5 أو أقل) = شاذ
    """
    model = _load_model()
    vec = _vector_from_features(features)
    score = model.decision_function(vec)[0]
    return float(score)


if __name__ == "__main__":
    # يسمح لك بتدريب النموذج عن طريق:
    # python -m app.model
    print("[model] بدء تدريب النموذج من خلال main ...")
    train_model()
