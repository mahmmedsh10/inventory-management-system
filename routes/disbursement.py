"""
routes/disbursement.py
=========================
مسارات فواتير الصرف (Disbursement Invoices Routes)
------------------------------------------------------------
كل منطق الأعمال موجود في services/disbursement_service.py (بما في ذلك
التحقق من كفاية الرصيد ومنطق FEFO عند الاعتماد). هذا الملف مسؤول فقط
عن التحقق من صحة المدخلات، استدعاء الخدمة، والاستجابة للمستخدم.
"""
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database import get_db
from services import disbursement_service
from utils.constants import STATUS_DRAFT
from utils.decorators import login_required, permission_required
from utils.validators import parse_invoice_rows

disbursement_bp = Blueprint("disbursement", __name__, url_prefix="/disbursements")


@disbursement_bp.route("", endpoint="list")
@login_required
def list_disbursements():
    """تعرض قائمة كل فواتير الصرف بكل حالاتها."""
    rows = disbursement_service.list_disbursement_invoices(get_db())
    return render_template("invoices_list.html", rows=rows, kind="disbursement",
                           title="فواتير الصرف")


@disbursement_bp.route("/new", methods=["GET", "POST"], endpoint="new")
@login_required
def new_disbursement():
    """تعرض نموذج فاتورة صرف جديدة (GET)، وتُنشئها كمسودة (POST)."""
    db = get_db()

    if request.method == "POST":
        rows, error = parse_invoice_rows("unit_price")
        if error:
            flash(error, "error")
            return render_template("disbursement_form.html",
                                   **disbursement_service.get_disbursement_form_context(db))

        invoice_id, number = disbursement_service.create_draft_disbursement(
            db, rows,
            request.form.get("customer_id") or None,
            request.form.get("invoice_date") or date.today().isoformat(),
            request.form.get("notes", "").strip(),
            g.user["user_id"],
        )
        db.commit()
        flash(f"تم حفظ الفاتورة {number} كمسودة", "success")
        return redirect(url_for("disbursement.view", invoice_id=invoice_id))

    return render_template("disbursement_form.html",
                           **disbursement_service.get_disbursement_form_context(db))


@disbursement_bp.route("/<int:invoice_id>", endpoint="view")
@login_required
def view_disbursement(invoice_id):
    """تعرض تفاصيل فاتورة صرف واحدة بكامل سطورها."""
    db = get_db()
    invoice = disbursement_service.get_disbursement_invoice_header(db, invoice_id)
    if invoice is None:
        abort(404)

    details = disbursement_service.get_disbursement_invoice_details(db, invoice_id)
    return render_template("invoice_view.html", inv=invoice, details=details,
                           kind="disbursement", title="فاتورة صرف")


@disbursement_bp.route("/<int:invoice_id>/edit", methods=["GET", "POST"], endpoint="edit")
@login_required
def edit_disbursement(invoice_id):
    """تعديل فاتورة صرف ما زالت مسودة فقط."""
    db = get_db()
    invoice = disbursement_service.get_disbursement_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)
    if invoice["status"] != STATUS_DRAFT:
        flash("لا يمكن تعديل فاتورة غير مسودة — ألغِ الاعتماد أولاً", "error")
        return redirect(url_for("disbursement.view", invoice_id=invoice_id))

    if request.method == "POST":
        rows, error = parse_invoice_rows("unit_price")
        if error:
            flash(error, "error")
        else:
            disbursement_service.update_draft_disbursement(
                db, invoice, rows,
                request.form.get("customer_id") or None,
                request.form.get("invoice_date") or None,
                request.form.get("notes", "").strip(),
            )
            db.commit()
            flash("تم حفظ التعديلات", "success")
            return redirect(url_for("disbursement.view", invoice_id=invoice_id))

    details = disbursement_service.get_disbursement_invoice_details(db, invoice_id)
    return render_template(
        "disbursement_form.html",
        **disbursement_service.get_disbursement_form_context(db, invoice, details),
    )


@disbursement_bp.route("/<int:invoice_id>/approve", methods=["POST"], endpoint="approve")
@permission_required("can_approve_disbursements")
def approve_disbursement(invoice_id):
    """تعتمد الفاتورة وتخصم الكميات من المخزون بنظام FEFO."""
    db = get_db()
    invoice = disbursement_service.get_disbursement_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = disbursement_service.approve_disbursement(db, invoice, g.user["user_id"])
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("disbursement.view", invoice_id=invoice_id))


@disbursement_bp.route("/<int:invoice_id>/unapprove", methods=["POST"], endpoint="unapprove")
@permission_required("can_unapprove_invoices")
def unapprove_disbursement(invoice_id):
    """تُلغي اعتماد الفاتورة وتعيد الكميات للمخزون وللدفعات الأصلية."""
    db = get_db()
    invoice = disbursement_service.get_disbursement_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = disbursement_service.unapprove_disbursement(db, invoice)
    db.commit()
    flash(message, "success" if success else "error")

    if success:
        return redirect(url_for("disbursement.edit", invoice_id=invoice_id))
    return redirect(url_for("disbursement.view", invoice_id=invoice_id))


@disbursement_bp.route("/<int:invoice_id>/cancel", methods=["POST"], endpoint="cancel")
@login_required
def cancel_disbursement(invoice_id):
    """تُلغي الفاتورة إذا كانت لا تزال مسودة."""
    db = get_db()
    invoice = disbursement_service.get_disbursement_invoice_raw(db, invoice_id)
    if invoice is None:
        abort(404)

    success, message = disbursement_service.cancel_disbursement(db, invoice)
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("disbursement.list"))
