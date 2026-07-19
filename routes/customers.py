"""
routes/customers.py
=====================
مسارات الجهات المستفيدة / العملاء (Customers Routes)
------------------------------------------------------------
شاشة بسيطة لعرض وإضافة الجهات المستفيدة، تُستخدم في فواتير الصرف.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from database import get_db
from services import inventory_service
from utils.decorators import login_required

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


@customers_bp.route("", methods=["GET", "POST"], endpoint="index")
@login_required
def index():
    """
    الوصف: تعرض قائمة الجهات المستفيدة النشطة (GET)، وتضيف جهة جديدة
    عند إرسال النموذج (POST) إذا كان الاسم غير فارغ.

    المعاملات: لا يوجد (تُقرأ من request.form عند POST).
    القيمة المرجعة: استجابة HTML (partners.html) أو إعادة توجيه.
    """
    db = get_db()

    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        if name:
            inventory_service.create_customer(
                db, name, request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
            )
            db.commit()
            flash("تمت إضافة الجهة", "success")
        return redirect(url_for("customers.index"))

    rows = inventory_service.list_active_customers(db)
    return render_template("partners.html", rows=rows, kind="جهة",
                           title="الجهات المستفيدة", name_field="customer_name")
