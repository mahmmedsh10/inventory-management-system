# ==============================================================
# أدوات المصادقة والمستخدمين
# ==============================================================
from flask import session, g
from database import get_db


def current_user():
    """
    الحصول على بيانات المستخدم الحالي
    
    الوصف:
    تستخرج بيانات المستخدم من الجلسة وتجلب معلوماته من قاعدة البيانات
    مع صلاحياته الكاملة.
    
    القيمة المرجعة:
    كائن sqlite3.Row يحتوي على بيانات المستخدم والصلاحيات
    أو None إذا كان المستخدم غير مسجل الدخول
    """
    if "user_id" not in session:
        return None
    
    # استعلام يجلب بيانات المستخدم مع كل صلاحياته من جدول الأدوار
    user = get_db().execute("""
        SELECT u.*, r.role_name,
               r.can_edit_prices, r.can_delete_items,
               r.can_approve_purchases, r.can_approve_disbursements,
               r.can_unapprove_invoices, r.can_approve_writeoffs, r.can_manage_users
        FROM users u 
        JOIN roles r ON r.role_id = u.role_id
        WHERE u.user_id = ? AND u.is_active = 1
    """, (session["user_id"],)).fetchone()
    
    return user


def has_permission(permission_name):
    """
    التحقق من وجود صلاحية معينة للمستخدم الحالي
    
    الوصف:
    تتحقق من أن المستخدم الحالي لديه الصلاحية المطلوبة.
    
    المعاملات:
    permission_name : اسم الصلاحية (مثل: can_approve_purchases)
    
    القيمة المرجعة:
    True إذا كان المستخدم لديه الصلاحية، False وإلا
    """
    user = current_user()
    if user is None:
        return False
    
    return bool(user[permission_name])


def get_user_by_id(user_id):
    """
    جلب بيانات مستخدم معين من قاعدة البيانات
    
    الوصف:
    تستخرج بيانات المستخدم بناءً على معرّفه.
    
    المعاملات:
    user_id : معرّف المستخدم
    
    القيمة المرجعة:
    كائن sqlite3.Row أو None إذا لم يُعثر على المستخدم
    """
    return get_db().execute("""
        SELECT u.*, r.role_name FROM users u
        JOIN roles r ON r.role_id = u.role_id
        WHERE u.user_id = ?
    """, (user_id,)).fetchone()


def get_all_users():
    """
    جلب قائمة بجميع المستخدمين
    
    الوصف:
    تجلب جميع المستخدمين مع بيانات أدوارهم.
    
    القيمة المرجعة:
    قائمة من كائنات sqlite3.Row
    """
    return get_db().execute("""
        SELECT u.*, r.role_name FROM users u
        JOIN roles r ON r.role_id = u.role_id
        ORDER BY u.user_id
    """).fetchall()


def get_all_roles():
    """
    جلب قائمة بجميع الأدوار المتاحة
    
    الوصف:
    تجلب جميع الأدوار المعرّفة في النظام.
    
    القيمة المرجعة:
    قائمة من كائنات sqlite3.Row
    """
    return get_db().execute(
        "SELECT * FROM roles ORDER BY role_id"
    ).fetchall()


def username_exists(username):
    """
    التحقق من وجود اسم مستخدم معين
    
    الوصف:
    تتحقق من أن اسم المستخدم لم يُستخدم من قبل.
    
    المعاملات:
    username : اسم المستخدم المراد البحث عنه
    
    القيمة المرجعة:
    True إذا كان موجوداً، False وإلا
    """
    return get_db().execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username,)
    ).fetchone() is not None


def toggle_user_status(user_id):
    """
    تفعيل أو تعطيل حساب المستخدم
    
    الوصف:
    تعكس حالة المستخدم (نشط/معطّل).
    
    المعاملات:
    user_id : معرّف المستخدم
    
    القيمة المرجعة:
    True عند نجاح العملية
    """
    db = get_db()
    db.execute(
        "UPDATE users SET is_active = 1 - is_active WHERE user_id = ?",
        (user_id,)
    )
    db.commit()
    return True
