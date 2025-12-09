from flask import Flask
from database import init_db
from app.routes import main_bp

def create_app():
    app = Flask(__name__)

    init_db()  # مهم

    app.register_blueprint(main_bp)

    # ----------------------------------------
    # 🔐 إضافة Security Headers بشكل آمن
    # ----------------------------------------
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    return app
