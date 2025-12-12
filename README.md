# SND — Smart Behavior-Based Risk Engine
SND is a lightweight behavior-based risk scoring system that simulates a user baseline and evaluates incoming events in real time.
It produces an action decision: *Allow / Alert / Challenge / Block*.

## Features
- Real-time risk scoring (AI + rules)
- User behavioral baseline concept
- Simple Flask web dashboard
- SQLite event logging (auto-created at runtime)

## Tech Stack
- Python 3.10+
- Flask
- scikit-learn (IsolationForest)
- SQLite (built-in)

## Quick Start (Ubuntu)
```bash
git clone https://github.com/Eng-Abdulrahman-Abdullah/SND.git
username = Eng-Abdulrahman-Abdullah
pass = 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

cd SND

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip

Access
	•	Health: http://127.0.0.1:5000/health
	•	Dashboard: http://127.0.0.1:5000/dashboard

Notes
	•	This project runs locally for demo/testing purposes.
	•	Any runtime database files are generated automatically and are ignored by Git.
pip install -r requirements.txt

python run.py
