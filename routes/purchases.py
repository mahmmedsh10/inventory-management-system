"""
routes/purchases.py
=====================
مسارات فواتير الشراء (Purchase Invoices Routes)
-----------------------------------------------------
كل منطق الأعمال (إنشاء، تعديل، اعتماد، إلغاء اعتماد، إلغاء) موجود في
services/purchase_service.py. هذا الملف مسؤول فقط عن: التحقق من صحة
المدخلات القادمة من النموذج، استدعاء دالة الخدمة المناسبة، ثم تنفيذ
commit() وعرض رسالة النتيجة (flash) وإعادة التوجيه.
"""
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database import get_db
from services import purchase_service
from utils.constants import STATUS_DRAFT
from utils.decorators import login_required, permission_required
from utils.validators import parse_invoice_rows

purchases_bp = Blueprint("purchases", __name__, url_prefix="/purchases")


@purchases_bp.route("", endpoint="list")
@login_required
def list_purchases():
    """تعرض قائمة كل فواتير الشراء بكل حالاتها."""
    rows = purchase_service.list_purchase_invoices(get_db())
    return render_template("invoices_list.html", rows=rows, kind="purchase",
                           title="فواتير الشراء")


@purchases_bp.route("/new", methods=["GET", "POST"], endpoint="new")
@login_required
def new_purchase():
    """
    الوصف: تعرض نموذج فاتورة شراء جديدة (GET)، وتُنشئها كمسودة (POST)
    بعد التحقق من صحة سطور الأصناف المُدخلة.

    المعاملات: لا يوجد (تُقرأ من request.form).
    القيمة المرجعة: استجابة HTML أو إعادة توجيه لعرض الفاتورة الجديدة.
    """
    db = get_db()

    if request.method == "POST":
        rows, error = parse_invoice_rows("price")
        if error:
            flash(error, "error")
            return render_template("purchase_form.html",
                                   **purchase_service.get_purchase_form_context(db))

        invoice_id, number = purchase_service.create_draft_purchase(
            db, rows,
            request.form.get("supplier_id") or None,
            request.form.get("invoice_date") or date.today().isoformat(),
            request.form.get("notes", "").strip(),
            g.user["user_id"],
        )
        db.commit()
        flash(f"تم حفظ الفاتورة {number} كمسودة", "success")
        return redirect(url_for("purchases.view", invoice_id=invoice_id))

    return render_template("purchase_form.html",
                           **purchase_service.get_purchase_form_context(db))


@purchases_bp.route("/<int:invoice_id>", endpoint="view")
@login_required
def view_purchase(invoice_id):
    """تعرض تفاصيل فاتورة شراء واحدة بكامل سطورها."""
    db = get_db()
    invoice = purchase_service.get_purchase_invoice_header(db, invoice_id)
    if invoice is None:
        abort(404)

    details = purchase_service.get_purchase_invoice_details(db, invoice_id)
    return render_template("invoice_view.html", inv=invoice, details=details,
                           kind="purchase", title="فاتورة شراء")


@purchases_bp.route("/<int:invoice_id>/edit", methods=["GET", "POST"], endpoint="edit")
@login_required
def edit_purchase(invoice_id):
    """
    الوصف: تعديل فاتورة شراء ما زالت مسودة فقط — الفواتير المعتمدة
    يجب إلغاء اعتمادها أولاً (عبر unapprove_purchase) قبل إتاحة تعديلها.
    """
    db = get_db()
    invoice = purchase_service.get_purchase_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)
    if invoice["status"] != STATUS_DRAFT:
        flash("لا يمكن تعديل فاتورة غير مسودة — ألغِ الاعتماد أولاً", "error")
        return redirect(url_for("purchases.view", invoice_id=invoice_id))

    if request.method == "POST":
        rows, error = parse_invoice_rows("price")
        if error:
            flash(error, "error")
        else:
            purchase_service.update_draft_purchase(
                db, invoice, rows,
                request.form.get("supplier_id") or None,
                request.form.get("invoice_date") or None,
                request.form.get("notes", "").strip(),
            )
            db.commit()
            flash("تم حفظ التعديلات", "success")
            return redirect(url_for("purchases.view", invoice_id=invoice_id))

    details = purchase_service.get_purchase_invoice_details(db, invoice_id)
    return render_template(
        "purchase_form.html",
        **purchase_service.get_purchase_form_context(db, invoice, details),
    )


@purchases_bp.route("/<int:invoice_id>/approve", methods=["POST"], endpoint="approve")
@permission_required("can_approve_purchases")
def approve_purchase(invoice_id):
    """تعتمد الفاتورة وتضيف كمياتها للمخزون (راجع purchase_service.approve_purchase)."""
    db = get_db()
    invoice = purchase_service.get_purchase_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = purchase_service.approve_purchase(db, invoice, g.user["user_id"])
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("purchases.view", invoice_id=invoice_id))


@purchases_bp.route("/<int:invoice_id>/unapprove", methods=["POST"], endpoint="unapprove")
@permission_required("can_unapprove_invoices")
def unapprove_purchase(invoice_id):
    """تُلغي اعتماد الفاتورة بعد التحقق من إمكانية ذلك (راجع purchase_service.unapprove_purchase)."""
    db = get_db()
    invoice = purchase_service.get_purchase_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = purchase_service.unapprove_purchase(db, invoice)
    db.commit()
    flash(message, "success" if success else "error")

    if success:
        return redirect(url_for("purchases.edit", invoice_id=invoice_id))
    return redirect(url_for("purchases.view", invoice_id=invoice_id))


@purchases_bp.route("/<int:invoice_id>/cancel", methods=["POST"], endpoint="cancel")
@login_required
def cancel_purchase(invoice_id):
    """تُلغي الفاتورة إذا كانت لا تزال مسودة."""
    db = get_db()
    invoice = purchase_service.get_purchase_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = purchase_service.cancel_purchase(db, invoice)
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("purchases.list"))
