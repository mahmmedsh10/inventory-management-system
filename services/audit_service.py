"""
services/audit_service.py
============================
خدمة سجل التدقيق (Audit Log Service)
-----------------------------------------
مسؤولة عن تسجيل كل عملية مهمة (إضافة، تعديل، اعتماد، إلغاء اعتماد،
إلغاء) في جدول audit_log لأغراض التتبع والمساءلة.
"""
from flask import session
from database import get_db


def log_action(action, entity=None, entity_id=None, details=None):
    """
    الوصف: تُدرج سجلاً جديداً في جدول audit_log يوثّق عملية قام بها المستخدم الحالي.
    المعاملات: action (وصف)، entity (جدول)، entity_id (رقم)، details (تفاصيل).
    القيمة المرجعة: لا يوجد.
    """
    get_db().execute(
        "INSERT INTO audit_log (user_id, action, entity, entity_id, details) "
        "VALUES (?,?,?,?,?)",
        (session.get("user_id"), action, entity, entity_id, details),
    )
