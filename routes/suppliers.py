"""
routes/suppliers.py
=====================
مسارات الموردين (Suppliers Routes)
----------------------------------------
شاشة بسيطة لعرض وإضافة الموردين، تُستخدم قوالبها المشتركة
(partners.html) أيضاً في شاشة العملاء (routes/customers.py).
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from database import get_db
from services import inventory_service
from utils.decorators import login_required

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")


@suppliers_bp.route("", methods=["GET", "POST"], endpoint="index")
@login_required
def index():
    """
    الوصف: تعرض قائمة الموردين النشطين (GET)، وتضيف مورداً جديداً
    عند إرسال النموذج (POST) إذا كان الاسم غير فارغ.

    المعاملات: لا يوجد (تُقرأ من request.form عند POST).
    القيمة المرجعة: استجابة HTML (partners.html) أو إعادة توجيه.
    """
    db = get_db()

    if request.method == "POST":
        name = request.form.get("supplier_name", "").strip()
        if name:
            inventory_service.create_supplier(
                db, name, request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
            )
            db.commit()
            flash("تمت إضافة المورد", "success")
        return redirect(url_for("suppliers.index"))

    rows = inventory_service.list_active_suppliers(db)
    return render_template("partners.html", rows=rows, kind="مورد",
                           title="الموردون", name_field="supplier_name")
