"""
app.py — نقطة تشغيل التطبيق الرئيسية (Application Entry Point)
استخدام نمط "مصنع التطبيق" (Application Factory) لإنشاء تطبيق Flask
"""
from datetime import date
from flask import Flask, render_template
from config import Config, warn_if_insecure_secret
from database import init_db, register_db
from routes import register_blueprints


def create_app(config_class=Config):
    """
    الوصف: تُنشئ وتُهيّئ نسخة تطبيق Flask كاملة.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    register_db(app)
    register_blueprints(app)
    _register_context_processors(app)
    _register_error_handlers(app)

    return app


def _register_context_processors(app):
    """حقن متغيرات عامة في كل القوالب"""
    @app.context_processor
    def inject_globals():
        from utils.auth import current_user
        return {"user": current_user(), "today": date.today().isoformat()}


def _register_error_handlers(app):
    """معالجات أخطاء عامة"""
    @app.errorhandler(404)
    def handle_not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_server_error(_error):
        return render_template("errors/500.html"), 500


# نسخة التطبيق التي يستوردها خادم WSGI
app = create_app()


if __name__ == "__main__":
    warn_if_insecure_secret()
    init_db(app)
    try:
        from waitress import serve
        print("النظام يعمل على: http://0.0.0.0:5000")
        serve(app, host="0.0.0.0", port=5000)
    except ImportError:
        app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
