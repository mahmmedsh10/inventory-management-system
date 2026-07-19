"""
routes/writeoff.py
=====================
مسارات أذونات الإعدام (Write-Off Routes)
--------------------------------------------
كل منطق الأعمال (إنشاء، تعديل، اعتماد نهائي، إلغاء) موجود في
services/writeoff_service.py. لا يوجد مسار "إلغاء اعتماد" لهذا النوع
من المستندات عمداً — الاعتماد هنا نهائي (راجع تعليقات الخدمة).
"""
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database import get_db
from services import writeoff_service
from utils.constants import STATUS_DRAFT, WRITEOFF_REASONS
from utils.decorators import login_required, permission_required
from utils.validators import parse_writeoff_rows

writeoff_bp = Blueprint("writeoff", __name__, url_prefix="/writeoffs")


@writeoff_bp.route("", endpoint="list")
@login_required
def list_writeoffs():
    """تعرض قائمة كل أذونات الإعدام بكل حالاتها."""
    rows = writeoff_service.list_writeoff_orders(get_db())
    return render_template("writeoffs_list.html", rows=rows)


@writeoff_bp.route("/new", methods=["GET", "POST"], endpoint="new")
@login_required
def new_writeoff():
    """
    الوصف:
    تعرض نموذج إذن إعدام جديد (GET)، مع دعم التعبئة المسبقة عند
    الفتح من رابط تنبيه صلاحية بلوحة التحكم عبر معاملات الرابط
    (?item_id=..&qty=..&reason=..)، وتُنشئ الإذن كمسودة (POST) بعد
    التحقق من صحة السبب والسطور.

    المعاملات: لا يوجد (تُقرأ من request.form أو request.args).
    القيمة المرجعة: استجابة HTML أو إعادة توجيه لعرض الإذن الجديد.
    """
    db = get_db()

    if request.method == "POST":
        reason = request.form.get("reason", "")
        if reason not in WRITEOFF_REASONS:
            flash("اختر سبب الإعدام", "error")
            return render_template("writeoff_form.html",
                                   **writeoff_service.get_writeoff_form_context(db))

        rows, error = parse_writeoff_rows(db)
        if error:
            flash(error, "error")
            return render_template("writeoff_form.html",
                                   **writeoff_service.get_writeoff_form_context(db))

        writeoff_id, number = writeoff_service.create_draft_writeoff(
            db, rows, reason,
            request.form.get("writeoff_date") or date.today().isoformat(),
            request.form.get("notes", "").strip(),
            g.user["user_id"],
        )
        db.commit()
        flash(f"تم حفظ إذن الإعدام {number} كمسودة — يعتمده المدير", "success")
        return redirect(url_for("writeoff.view", writeoff_id=writeoff_id))

    # دعم الفتح المسبق من تنبيه صنف منتهي الصلاحية في لوحة التحكم
    prefill = None
    if request.args.get("item_id"):
        prefill = writeoff_service.get_writeoff_prefill(
            db, request.args.get("item_id"),
            request.args.get("qty", ""),
            request.args.get("reason", "منتهي الصلاحية"),
        )

    return render_template("writeoff_form.html",
                           **writeoff_service.get_writeoff_form_context(db, prefill=prefill))


@writeoff_bp.route("/<int:writeoff_id>", endpoint="view")
@login_required
def view_writeoff(writeoff_id):
    """تعرض تفاصيل إذن إعدام واحد بكامل سطوره."""
    db = get_db()
    order = writeoff_service.get_writeoff_order_header(db, writeoff_id)
    if order is None:
        abort(404)

    details = writeoff_service.get_writeoff_order_details(db, writeoff_id)
    return render_template("writeoff_view.html", order=order, details=details)


@writeoff_bp.route("/<int:writeoff_id>/edit", methods=["GET", "POST"], endpoint="edit")
@login_required
def edit_writeoff(writeoff_id):
    """تعديل إذن إعدام ما زال مسودة فقط."""
    db = get_db()
    order = writeoff_service.get_writeoff_order_raw(db, writeoff_id)
    if order is None:
        abort(404)
    if order["status"] != STATUS_DRAFT:
        flash("لا يمكن تعديل إذن غير مسودة", "error")
        return redirect(url_for("writeoff.view", writeoff_id=writeoff_id))

    if request.method == "POST":
        reason = request.form.get("reason", "")
        if reason not in WRITEOFF_REASONS:
            rows, error = None, "اختر سبب الإعدام"
        else:
            rows, error = parse_writeoff_rows(db)

        if error:
            flash(error, "error")
        else:
            writeoff_service.update_draft_writeoff(
                db, order, rows, reason,
                request.form.get("writeoff_date") or None,
                request.form.get("notes", "").strip(),
            )
            db.commit()
            flash("تم حفظ التعديلات", "success")
            return redirect(url_for("writeoff.view", writeoff_id=writeoff_id))

    details = writeoff_service.get_writeoff_order_details(db, writeoff_id)
    return render_template(
        "writeoff_form.html",
        **writeoff_service.get_writeoff_form_context(db, order, details),
    )


@writeoff_bp.route("/<int:writeoff_id>/approve", methods=["POST"], endpoint="approve")
@permission_required("can_approve_writeoffs")
def approve_writeoff(writeoff_id):
    """تعتمد الإذن اعتماداً نهائياً وتخصم الكميات من المخزون بنظام FEFO."""
    db = get_db()
    order = writeoff_service.get_writeoff_order_raw(db, writeoff_id)
    if order is None:
        abort(404)

    success, message = writeoff_service.approve_writeoff(db, order, g.user["user_id"])
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("writeoff.view", writeoff_id=writeoff_id))


@writeoff_bp.route("/<int:writeoff_id>/cancel", methods=["POST"], endpoint="cancel")
@login_required
def cancel_writeoff(writeoff_id):
    """تُلغي الإذن إذا كان لا يزال مسودة."""
    db = get_db()
    order = writeoff_service.get_writeoff_order_raw(db, writeoff_id)
    if order is None:
        abort(404)

    success, message = writeoff_service.cancel_writeoff(db, order)
    db.commit()
    flash(message, "success" if success else "error")
    return redirect(url_for("writeoff.list"))
