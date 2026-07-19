"""مسارات المصادقة"""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from database import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """تسجيل الدخول"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = get_db().execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session["user_id"] = user["user_id"]
            return redirect(url_for("dashboard.index"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "error")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """تسجيل الخروج"""
    session.clear()
    return redirect(url_for("auth.login"))
