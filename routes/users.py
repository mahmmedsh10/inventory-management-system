"""
routes/users.py
=================
مسارات إدارة المستخدمين (Users Management Routes)
------------------------------------------------------------
شاشة محصورة بصلاحية can_manage_users (المدير افتراضياً) لإضافة
مستخدمين جدد وتفعيل/تعطيل الحسابات الحالية. الاستعلامات هنا بسيطة
بما يكفي لتبقى مباشرة في المسار دون الحاجة لخدمة منفصلة، لكنها موثّقة
بالكامل هنا لسهولة المراجعة.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database import get_db
from services.audit_service import log_action
from utils.decorators import permission_required

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("", methods=["GET", "POST"], endpoint="index")
@permission_required("can_manage_users")
def index():
    """
    الوصف:
    تعرض قائمة كل المستخدمين مع أدوارهم وحالتهم (GET)، وتضيف مستخدماً
    جديداً (POST) بعد التحقق من: تعبئة كل الحقول المطلوبة، وعدم وجود
    اسم مستخدم مكرر مسبقاً. كلمة المرور تُخزَّن مُشفَّرة دائماً
    (generate_password_hash) ولا تُحفَظ أبداً كنص صريح.

    المعاملات: لا يوجد (تُقرأ من request.form عند POST).
    القيمة المرجعة: استجابة HTML (users.html) أو إعادة توجيه.
    """
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        role_id = request.form.get("role_id")

        if not (username and full_name and password and role_id):
            flash("كل الحقول مطلوبة", "error")
        elif db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            flash("اسم المستخدم موجود بالفعل", "error")
        else:
            db.execute(
                "INSERT INTO users (username, full_name, password_hash, role_id) VALUES (?,?,?,?)",
                (username, full_name, generate_password_hash(password), role_id),
            )
            log_action("إضافة مستخدم", "users", None, username)
            db.commit()
            flash("تمت إضافة المستخدم", "success")

        return redirect(url_for("users.index"))

    rows = db.execute("""
        SELECT u.*, r.role_name FROM users u JOIN roles r ON r.role_id=u.role_id
        ORDER BY u.user_id
    """).fetchall()
    roles = db.execute("SELECT * FROM roles ORDER BY role_id").fetchall()
    return render_template("users.html", rows=rows, roles=roles)


@users_bp.route("/<int:user_id>/toggle", methods=["POST"], endpoint="toggle")
@permission_required("can_manage_users")
def toggle(user_id):
    """
    الوصف:
    تبدّل حالة تفعيل مستخدم (نشط ⇄ معطَّل). يُمنع المستخدم من تعطيل
    حسابه الخاص لتفادي إقفال وصوله عن طريق الخطأ.

    المعاملات: user_id.
    القيمة المرجعة: إعادة توجيه لقائمة المستخدمين.
    """
    if user_id == g.user["user_id"]:
        flash("لا يمكنك تعطيل حسابك", "error")
    else:
        db = get_db()
        db.execute("UPDATE users SET is_active = 1 - is_active WHERE user_id=?", (user_id,))
        db.commit()
        flash("تم تحديث حالة المستخدم", "success")

    return redirect(url_for("users.index"))
