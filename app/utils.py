import sqlite3

DB_PATH = "events.db"


def normalize_str(value: str) -> str:
    """
    تنظيف نص بسيط: إزالة الفراغات وتحويل إلى lowercase.
    مفيد للأسماء والمدن والأجهزة.
    """
    if not value:
        return ""
    return value.strip().lower()


def convert_city_to_region(city: str) -> str:
    """
    تحويل اسم المدينة إلى منطقة تقريبية في المملكة.

    المنطق:
    1) نحاول نستخدم lookup من جدول city_region في قاعدة البيانات (لو حاب تضيف مدن/قرى كثيرة لاحقاً).
    2) لو ما وجدنا بالجدول، نستخدم mapping بسيط داخل الكود (fallback).
    """

    if not city:
        return "unknown"

    raw = city.strip()
    norm = raw.lower()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # محاولة المطابقة من جدول city_region (لو كنت أنشأته لاحقاً)
    try:
        cur.execute(
            """
            SELECT region
            FROM city_region
            WHERE LOWER(name_ar) = LOWER(?)
               OR LOWER(name_en) = LOWER(?)
            LIMIT 1
            """,
            (raw, norm),
        )
        row = cur.fetchone()
    except sqlite3.OperationalError:
        # لو الجدول غير موجود، نتجاهل ونكمل على fallback
        row = None

    conn.close()

    if row and row[0]:
        return row[0]

    # fallback بسيط لبعض المدن الشائعة
    central = ["riyadh", "الرياض", "buraydah", "بريدة"]
    western = [
        "jeddah", "جدة",
        "makkah", "mecca", "مكة", "مكة المكرمة",
        "madinah", "medina", "المدينة", "المدينة المنورة"
    ]
    eastern = [
        "dammam", "الدمام",
        "khobar", "الخبر",
        "dhahran", "الظهران",
        "jubail", "الجبيل"
    ]
    southern = [
        "abha", "أبها",
        "khamis mushait", "خميس مشيط",
        "jazan", "جازان",
        "najran", "نجران"
    ]
    northern = [
        "tabuk", "تبوك",
        "hail", "حائل",
        "arar", "عرعر",
        "sakaka", "سكاكا"
    ]

    if norm in [normalize_str(c) for c in central]:
        return "central"
    if norm in [normalize_str(c) for c in western]:
        return "western"
    if norm in [normalize_str(c) for c in eastern]:
        return "eastern"
    if norm in [normalize_str(c) for c in southern]:
        return "southern"
    if norm in [normalize_str(c) for c in northern]:
        return "northern"

    return "unknown"


def get_time_window(hour: int) -> str:
    """
    تقسيم اليوم إلى نوافذ استخدام عامة:
    - night:    0–5
    - morning:  6–11
    - noon:    12–16
    - evening: 17–23
    """
    if hour < 0 or hour > 23:
        return "unknown"

    if 0 <= hour <= 5:
        return "night"
    elif 6 <= hour <= 11:
        return "morning"
    elif 12 <= hour <= 16:
        return "noon"
    else:
        return "evening"
