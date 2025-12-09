import requests
import time

BASE_URL = "http://127.0.0.1:5000/score"

def send(event):
    print(f"\n--- Sending event: {event['service']} from {event['city']} ---")
    r = requests.post(BASE_URL, json=event)
    print("Status:", r.status_code)
    print("Response:", r.json())

# 1) سيناريو طبيعي (Allow متوقع)
normal_event = {
    "user_id": "user_1",
    "device": "iphone",
    "city": "Riyadh",
    "region": "SA",
    "os": "iOS",
    "browser": "Safari",
    "service": "view_profile",
    "event_time": "2025-12-09T10:30:00"
}

# 2) مدينة جديدة + جهاز جديد (Alert / Challenge حسب السكور)
new_city_device = {
    "user_id": "user_1",
    "device": "new_laptop",
    "city": "Dubai",
    "region": "AE",
    "os": "Windows",
    "browser": "Chrome",
    "service": "change_mobile",
    "event_time": "2025-12-09T10:35:00"
}

# 3) خدمة حساسة مع سكّور عالي (Challenge متوقع)
sensitive_service = {
    "user_id": "user_2",
    "device": "android",
    "city": "Jeddah",
    "region": "SA",
    "os": "Android",
    "browser": "Chrome",
    "service": "reset_password",
    "event_time": "2025-12-09T10:40:00"
}

# 4) سبايك محاولات (Spike) لنفس المستخدم (يفعّل قاعدة 5 في الساعة)
def send_spike():
    base = {
        "user_id": "user_3",
        "device": "android",
        "city": "Riyadh",
        "region": "SA",
        "os": "Android",
        "browser": "Chrome",
        "service": "login",
    }
    for i in range(6):
        event = base.copy()
        event["event_time"] = f"2025-12-09T11:0{i}:00"
        send(event)
        time.sleep(0.3)

if __name__ == "__main__":
    send(normal_event)
    send(new_city_device)
    send(sensitive_service)
    send_spike()
