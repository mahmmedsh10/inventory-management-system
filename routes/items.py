"""
routes/items.py
=================
مسارات الأصناف (Items Routes)
------------------------------------
شاشات عرض/إضافة/تعديل/حذف الأصناف. كل استعلامات وتحديثات قاعدة
البيانات موجودة في services/inventory_service.py، وهذا الملف مسؤول
فقط عن: قراءة الطلب، التحقق من صحة المدخلات، استدعاء الخدمة، وعرض
النتيجة أو إعادة التوجيه المناسبة.
"""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from database import get_db
from services import inventory_service
from utils.decorators import login_required, permission_required
from utils.validators import parse_float_field, parse_int_field

items_bp = Blueprint("items", __name__, url_prefix="/items")


@items_bp.route("", endpoint="list")
@login_required
def list_items():
    """
    الوصف: تعرض قائمة كل الأصناف النشطة.
    المعاملات: لا يوجد.
    القيمة المرجعة: استجابة HTML (items.html).
    """
    rows = inventory_service.list_active_items(get_db())
    return render_template("items.html", items=rows)


@items_bp.route("/new", methods=["GET", "POST"], endpoint="new")
@login_required
def new_item():
    """
    الوصف:
    تعرض نموذج إضافة صنف جديد (GET)، وتتحقق من صحة المدخلات وتنشئ
    الصنف (POST). الكمية وحد التنبيه يجب أن يكونا أعداداً صحيحة غير
    سالبة، وسعر الشراء رقماً عشرياً غير سالب.

    المعاملات: لا يوجد (تُقرأ من request.form).
    القيمة المرجعة: استجابة HTML أو إعادة توجيه لقائمة الأصناف.
    """
    if request.method == "POST":
        name = request.form.get("item_name", "").strip()
        quantity = parse_int_field("quantity")
        reorder_level = parse_int_field("reorder_level")
        price = parse_float_field("purchase_price")

        if not name or None in (quantity, reorder_level, price):
            flash("تأكد من إدخال الاسم وقيم غير سالبة", "error")
            return render_template("item_form.html", item=None)

        db = get_db()
        unit = request.form.get("unit", "").strip() or "قطعة"
        inventory_service.create_item(
            db, name, quantity, reorder_level, price, request.form.get("notes", "").strip(), unit
        )
        db.commit()
        flash("تمت إضافة الصنف بنجاح", "success")
        return redirect(url_for("items.list"))

    return render_template("item_form.html", item=None)


@items_bp.route("/<int:item_id>/edit", methods=["GET", "POST"], endpoint="edit")
@login_required
def edit_item(item_id):
    """
    الوصف:
    تعرض نموذج تعديل صنف موجود (GET)، وتحدّث بياناته (POST). سعر
    الشراء لا يُعدَّل إلا إذا كان المستخدم الحالي يملك صلاحية
    can_edit_prices (يُفرض هذا القيد أيضاً داخل
    services.inventory_service.update_item كحماية مزدوجة).

    المعاملات: item_id (رقم الصنف من رابط الصفحة).
    القيمة المرجعة: استجابة HTML أو إعادة توجيه لقائمة الأصناف.
    """
    db = get_db()
    item = inventory_service.get_active_item(db, item_id)
    if item is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("item_name", "").strip()
        reorder_level = parse_int_field("reorder_level")
        if not name or reorder_level is None:
            flash("تأكد من إدخال الاسم وقيم غير سالبة", "error")
            return render_template("item_form.html", item=item)

        can_edit_prices = bool(g.user["can_edit_prices"])
        new_price = parse_float_field("purchase_price") if can_edit_prices else None
        unit = request.form.get("unit", "").strip() or "قطعة"

        success = inventory_service.update_item(
            db, item, name, reorder_level, request.form.get("notes", "").strip(),
            new_price, can_edit_prices, unit,
        )
        if not success:
            flash("السعر غير صالح", "error")
            return render_template("item_form.html", item=item)

        db.commit()
        flash("تم حفظ التعديلات", "success")
        return redirect(url_for("items.list"))

    return render_template("item_form.html", item=item)


@items_bp.route("/<int:item_id>/delete", methods=["POST"], endpoint="delete")
@permission_required("can_delete_items")
def delete_item(item_id):
    """
    الوصف: تحذف صنفاً حذفاً ناعماً (is_active=0). تتطلب صلاحية
    can_delete_items، والتي يتحقق منها المُزخرِف permission_required
    قبل تنفيذ الدالة.

    المعاملات: item_id.
    القيمة المرجعة: إعادة توجيه لقائمة الأصناف.
    """
    db = get_db()
    item = inventory_service.soft_delete_item(db, item_id)
    if item is None:
        abort(404)

    db.commit()
    flash("تم حذف الصنف", "success")
    return redirect(url_for("items.list"))
