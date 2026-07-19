"""
config.py
=========
إعدادات التطبيق (Configuration)
--------------------------------
يجمع هذا الملف كل الإعدادات القابلة للتهيئة في مكان واحد بدلاً من تبعثرها
داخل app.py، ويقرأ القيم الحساسة (مثل المفتاح السري) من متغيرات البيئة
بدلاً من كتابتها مباشرة في الكود المصدري (Hardcoding)، وهو ما يمثل
تحسيناً أمنياً أساسياً مقارنة بالنسخة السابقة.
"""
import os
import secrets
from pathlib import Path

# المسار الجذري للمشروع (المجلد الذي يحتوي على app.py)
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """
    الوصف:
    كلاس الإعدادات الأساسي الذي يُحمَّل في التطبيق عبر app.config.from_object().

    ملاحظات أمنية:
    - SECRET_KEY يُقرأ من متغير البيئة SECRET_KEY إن وُجد.
      في حال عدم توفره (بيئة تطوير محلية فقط) يتم توليد مفتاح عشوائي
      آمن مؤقت بدلاً من استخدام قيمة ثابتة معروفة، مع طباعة تحذير.
    - SESSION_COOKIE_HTTPONLY و SESSION_COOKIE_SAMESITE يحسّنان حماية
      جلسة المستخدم من هجمات XSS و CSRF البسيطة.
    """

    # مفتاح تشفير الجلسات (Session) — يجب ضبطه دائماً في بيئة الإنتاج
    # عبر متغير البيئة SECRET_KEY
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # مسار قاعدة بيانات SQLite
    DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "instance" / "inventory.db"))

    # مسار ملف تعريف الجداول الأساسي
    SCHEMA_PATH = BASE_DIR / "schema.sql"

    # عدد الأيام التي تُعتبر بعدها الدفعة "قريبة من الانتهاء"
    # (محجوزة للاستخدام المستقبلي في طبقة الخدمات؛ منطق التنبيه الحالي
    # مطبَّق داخل schema.sql عبر v_expiry_alerts للحفاظ على نفس السلوك)
    NEAR_EXPIRY_DAYS = int(os.environ.get("NEAR_EXPIRY_DAYS", 30))

    # حماية إضافية لكوكيز الجلسة
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # عدم عرض تفاصيل الأخطاء التقنية (Stack Trace) للمستخدم النهائي
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    PROPAGATE_EXCEPTIONS = False


def warn_if_insecure_secret():
    """
    الوصف:
    يطبع تحذيراً في الطرفية إذا لم يتم ضبط SECRET_KEY عبر متغير البيئة،
    لتنبيه المسؤول عن النظام قبل نشر التطبيق في بيئة إنتاج حقيقية.
    تُستدعى هذه الدالة مرة واحدة عند إقلاع التطبيق.
    """
    if not os.environ.get("SECRET_KEY"):
        print(
            "⚠️  تحذير أمني: لم يتم ضبط متغير البيئة SECRET_KEY. "
            "تم توليد مفتاح مؤقت تلقائياً. لا تستخدم هذا الإعداد في بيئة الإنتاج — "
            "اضبط SECRET_KEY في متغيرات البيئة قبل النشر."
        )
