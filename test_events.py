import requests
import time
from datetime import datetime, timedelta

URL = "http://127.0.0.1:5000/score"

# -----------------------
# Helpers
# -----------------------

def send(user, device, city, service, minutes_ago=0):
    event_time = datetime.now() - timedelta(minutes=minutes_ago)
    payload = {
        "user_id": user,
        "device": device,
        "city": city,
        "service": service,
        "event_time": event_time.isoformat(),
    }

    print("\n>>> Sending event:", payload)
    r = requests.post(URL, json=payload)
    print("<<< Response:", r.json())
    time.sleep(0.2)


# ============================
# USERS
# ============================

U1 = "User1"
U2 = "User2"
U3 = "User3"
U4 = "User4"

# ============================
# SCENARIO: 50 EVENTS
# ============================

def run_tests():

    # -----------------------------------------
    # 1) Normal baseline behavior (Abdulrahman)
    # -----------------------------------------
    for i in range(10):
        send(U1, "iPhone", "Riyadh", "view_profile", minutes_ago=60 - i)

    # -----------------------------------------
    # 2) Slight anomalies but still normal (Abdulrahman)
    # -----------------------------------------
    send(U1, "iPhone", "Riyadh", "renew_id")
    send(U1, "iPhone", "Riyadh", "pay_bills")

    # -----------------------------------------
    # 3) Device change (Abdulrahman)
    # -----------------------------------------
    send(U1, "Windows-PC", "Riyadh", "view_profile")

    # -----------------------------------------
    # 4) New city moderate risk (Abdulrahman)
    # -----------------------------------------
    send(U1, "iPhone", "Jeddah", "view_profile")

    # -----------------------------------------
    # 5) Sensitive service + new city (Abdulrahman)
    # -----------------------------------------
    send(U1, "iPhone", "Jeddah", "reset_password")

    # -----------------------------------------
    # 6) High spike (Abdulrahman)
    # -----------------------------------------
    for i in range(5):
        send(U1, "iPhone", "Riyadh", "login", minutes_ago=i)

    # -----------------------------------------
    # 7) Normal baseline for Nasser
    # -----------------------------------------
    for i in range(8):
        send(U2, "Galaxy", "Dammam", "view_profile", minutes_ago=90 - i)

    # -----------------------------------------
    # 8) New device (Nasser)
    # -----------------------------------------
    send(U2, "Windows-Laptop", "Dammam", "renew_license")

    # -----------------------------------------
    # 9) Sensitive service (Nasser)
    # -----------------------------------------
    send(U2, "Galaxy", "Dammam", "change_mobile")

    # -----------------------------------------
    # 10) Attempt risky login from new city (Nasser)
    # -----------------------------------------
    send(U2, "Galaxy", "Medina", "login")

    # -----------------------------------------
    # 11) Dalal—Warm clean baseline
    # -----------------------------------------
    for i in range(6):
        send(U3, "iPhone", "Riyadh", "view_profile", minutes_ago=30 - i)

    # -----------------------------------------
    # 12) Dalal—Sensitive service
    # -----------------------------------------
    send(U3, "iPhone", "Riyadh", "reset_password")

    # -----------------------------------------
    # 13) Dalal—City change mid-risk
    # -----------------------------------------
    send(U3, "iPhone", "Abha", "login")

    # -----------------------------------------
    # 14) Najla—new user warm start
    # -----------------------------------------
    send(U4, "Huawei", "Tabuk", "view_profile")
    send(U4, "Huawei", "Tabuk", "view_profile")
    send(U4, "Huawei", "Tabuk", "renew_id")

    # -----------------------------------------
    # 15) Najla—new device (should trigger alert/challenge)
    # -----------------------------------------
    send(U4, "MacBook", "Tabuk", "login")

    # -----------------------------------------
    # 16) Najla—Sensitive + new city
    # -----------------------------------------
    send(U4, "Huawei", "Jeddah", "reset_password")

    # -----------------------------------------
    # 17) Add some natural mixed events (to reach 50 total)
    # -----------------------------------------
    send(U1, "iPhone", "Riyadh", "e-service")
    send(U1, "iPhone", "Riyadh", "otp_request")

    send(U2, "Galaxy", "Dammam", "otp_request")
    send(U2, "Galaxy", "Dammam", "login")

    send(U3, "iPhone", "Riyadh", "pay_bills")
    send(U3, "iPhone", "Riyadh", "e-service")

    send(U4, "Huawei", "Tabuk", "otp_request")
    send(U4, "Huawei", "Tabuk", "pay_bills")


if __name__ == "__main__":
    run_tests()
