# SND — Smart Behavior-Based Risk Engine

SND is a lightweight *behavior-based risk scoring system* designed as an MVP to demonstrate how user behavior can be analyzed in real time to detect abnormal or risky activity.

The system builds an *initial behavioral baseline per user*, then evaluates incoming events against that baseline to produce a decision:

*Allow / Alert / Challenge / Block*

---

## Problem Statement
Traditional security systems often rely on static rules.
SND explores a smarter approach by *understanding user behavior patterns* and detecting anomalies that may indicate fraud, misuse, or compromise.

---

## How It Works
1. User events are collected (time, frequency, behavior signals).
2. A baseline is established for each user.
3. Incoming events are evaluated using:
   - Machine learning (IsolationForest)
   - Simple risk rules
4. A risk score and action decision are produced in real time.

---

## Key Features
- Behavior-based risk scoring
- User baseline simulation
- Real-time decision engine
- Flask web dashboard
- SQLite event logging (auto-generated)

---

## Tech Stack
- Python 3.10+
- Flask
- scikit-learn (IsolationForest)
- SQLite (built-in, no setup required)

---

## Project Scope
- MVP 

---
## Quick Start (Ubuntu)

```bash
git clone https://github.com/Eng-Abdulrahman-Abdullah/SND.git
cd SND

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python run.py

Access URLs
	•	Health Check: http://127.0.0.1:5000/health
	•	Dashboard: http://127.0.0.1:5000/dashboard

⸻
## Notes
- The application runs locally.
- SQLite database files are generated automatically at runtime.
- Runtime files are ignored via .gitignore.
- No external services or APIs are required.
- This project is a functional MVP focusing on behavior-based risk scoring.
- AI decisions are simulated using IsolationForest for anomaly detection.
- The system is designed for clarity, extensibility, and demonstration purposes.




