import os
import sqlite3
from datetime import datetime, timedelta

# مسار قاعدة البيانات (نفس مجلد المشروع /SND)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")


# ---------------------- تهيئة قاعدة البيانات ---------------------- #

def init_db():
    """
    إنشاء جدول الأحداث إذا لم يكن موجودًا + إنشاء فهارس بسيطة.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # جدول الأحداث الرئيسي
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            device TEXT NOT NULL,
            city TEXT NOT NULL,
            region TEXT,
            os TEXT,
            browser TEXT,
            service TEXT NOT NULL,
            event_time TEXT NOT NULL,
            timestamp_ms INTEGER,
            risk_score REAL NOT NULL,
            ai_risk_score REAL,
            rules_score REAL,
            decision TEXT NOT NULL,
            raw_payload TEXT
        );
        """
    )

    # فهارس لتحسين الاستعلامات
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_events_user_ts
        ON events (user_id, timestamp_ms);
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_events_user_service
        ON events (user_id, service);
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_events_user_city_device
        ON events (user_id, city, device);
        """
    )

    conn.commit()
    conn.close()


# ---------------------- إدخال الأحداث ---------------------- #

def insert_event(
    user_id: str,
    device: str,
    city: str,
    region: str,
    os_name: str,
    browser: str,
    service: str,
    event_time: str,
    timestamp_ms: int,
    risk_score: float,
    ai_risk_score: float,
    rules_score: float,
    decision: str,
    raw_payload: str,
):
    """
    تخزين الحدث في جدول events.

    ملاحظة مهمة:
    - نمنع "تسميم" البصمة السلوكية عن طريق عدم حفظ الأحداث عالية الخطورة في التعلم.
    - لكننا ما زلنا نسمح بحفظ الأحداث ذات المخاطر المنخفضة والمتوسطة.
    """
    # لا نحفظ إلا الأحداث ذات المخاطر <= 90 تقريباً (تقدر تشددها لاحقاً إن حبيت)
    # لو تبي بصمة أنظف جدًا خلي الشرط <= 35 كما ناقشنا سابقًا.
    if risk_score > 95:
        # أحداث شديدة السوء، نتجاهلها من التخزين بالكامل
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO events (
            user_id,
            device,
            city,
            region,
            os,
            browser,
            service,
            event_time,
            timestamp_ms,
            risk_score,
            ai_risk_score,
            rules_score,
            decision,
            raw_payload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            device,
            city,
            region,
            os_name,
            browser,
            service,
            event_time,
            timestamp_ms,
            risk_score,
            ai_risk_score,
            rules_score,
            decision,
            raw_payload,
        ),
    )

    conn.commit()
    conn.close()


# ---------------------- دوال مساعدة لاسترجاع البيانات ---------------------- #

def get_last_event(user_id: str):
    """
    إرجاع آخر حدث للمستخدم (للتحقق من سرعة الطلبات وغيرها).

    يعيد tuple:
        (event_time_str, device, city, timestamp_ms)
    أو None إذا لا توجد أحداث.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT event_time, device, city, timestamp_ms
        FROM events
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    )

    row = cur.fetchone()
    conn.close()
    return row  # ممكن تكون None


def get_event_count(user_id: str, last_minutes: int = 60) -> int:
    """
    عدد الأحداث للمستخدم خلال آخر last_minutes دقيقة.
    يعتمد على timestamp_ms (وقت وصول الطلب للنظام).
    """
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    cutoff_ms = now_ms - (last_minutes * 60 * 1000)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM events
        WHERE user_id = ?
          AND timestamp_ms IS NOT NULL
          AND timestamp_ms >= ?
        """,
        (user_id, cutoff_ms),
    )

    count = cur.fetchone()[0]
    conn.close()
    return int(count)


def get_low_risk_event_count(user_id: str) -> int:
    """
    عدد الأحداث منخفضة المخاطر للمستخدم (تُستخدم لتحديد is_new_user).
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM events
        WHERE user_id = ?
          AND risk_score <= 35
        """,
        (user_id,),
    )

    result = cur.fetchone()[0]
    conn.close()
    return int(result)


def get_event_stats(*args, **kwargs) -> dict:
    """
    إرجاع إحصائيات سريعة عن سلوك المستخدم تُستخدم في build_features.

    نحافظ على توقيع مرن حتى لو اختلفت طريقة الاستدعاء في processing.py:
        get_event_stats(user_id, device, city, service, event_dt)
    أو استدعاء باستخدام kwargs.

    الناتج:
        {
            "events_last_1h": int,
            "events_last_24h": int,
            "avg_daily_events": float,
            "city_frequency": float,
            "device_frequency": float,
            "service_frequency": float,
        }
    """
    # استخراج المعاملات بشكل مرن
    user_id = kwargs.get("user_id", args[0] if len(args) > 0 else None)
    device = kwargs.get("device", args[1] if len(args) > 1 else None)
    city = kwargs.get("city", args[2] if len(args) > 2 else None)
    service = kwargs.get("service", args[3] if len(args) > 3 else None)

    if user_id is None:
        # حالة احتياطية – يرجع قيم صفرية
        return {
            "events_last_1h": 0,
            "events_last_24h": 0,
            "avg_daily_events": 0.0,
            "city_frequency": 0.0,
            "device_frequency": 0.0,
            "service_frequency": 0.0,
        }

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) عدد الأحداث في آخر ساعة وآخر 24 ساعة
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    cutoff_1h = now_ms - (60 * 60 * 1000)
    cutoff_24h = now_ms - (24 * 60 * 60 * 1000)

    cur.execute(
        """
        SELECT COUNT(*)
        FROM events
        WHERE user_id = ?
          AND timestamp_ms IS NOT NULL
          AND timestamp_ms >= ?
        """,
        (user_id, cutoff_1h),
    )
    events_last_1h = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM events
        WHERE user_id = ?
          AND timestamp_ms IS NOT NULL
          AND timestamp_ms >= ?
        """,
        (user_id, cutoff_24h),
    )
    events_last_24h = cur.fetchone()[0]

    # 2) إجمالي عدد الأحداث وعدد الأيام المختلفة
    cur.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT DATE(event_time))
        FROM events
        WHERE user_id = ?
        """,
        (user_id,),
    )
    total_events, distinct_days = cur.fetchone()
    total_events = total_events or 0
    distinct_days = distinct_days or 0

    if distinct_days > 0:
        avg_daily_events = float(total_events) / float(distinct_days)
    else:
        avg_daily_events = 0.0

    # 3) تكرار المدينة/الجهاز/الخدمة
    def _freq_for(field_name: str, value: str | None) -> float:
        if not value or total_events == 0:
            return 0.0

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM events
            WHERE user_id = ?
              AND {field_name} = ?
            """,
            (user_id, value),
        )
        count = cur.fetchone()[0] or 0
        return float(count) / float(total_events)

    city_frequency = _freq_for("city", city)
    device_frequency = _freq_for("device", device)
    service_frequency = _freq_for("service", service)

    conn.close()

    return {
        "events_last_1h": int(events_last_1h),
        "events_last_24h": int(events_last_24h),
        "avg_daily_events": float(avg_daily_events),
        "city_frequency": float(city_frequency),
        "device_frequency": float(device_frequency),
        "service_frequency": float(service_frequency),
    }


def get_sequence_history(*args, **kwargs):
    """
    إرجاع تسلسل آخر الخدمات للمستخدم (لـ Sequence / Pattern).
    التوقيع مرن أيضاً:
        get_sequence_history(user_id, limit)
    أو get_sequence_history(user_id=user_id, limit=5)
    """
    user_id = kwargs.get("user_id", args[0] if len(args) > 0 else None)
    limit = kwargs.get("limit", args[1] if len(args) > 1 else 5)

    if user_id is None:
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT service, event_time
        FROM events
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, int(limit)),
    )

    rows = cur.fetchall()
    conn.close()

    # نرجع فقط قائمة بالخدمات بالترتيب من الأحدث للأقدم
    return [r[0] for r in rows]


def get_recent_events(limit: int = 50):
    """
    إرجاع آخر الأحداث (للاستخدام في الـ Dashboard).
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            device,
            city,
            region,
            os,
            browser,
            service,
            event_time,
            risk_score,
            ai_risk_score,
            rules_score,
            decision
        FROM events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows

