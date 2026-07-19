"""
routes/api.py
===============
مسارات API خفيفة (JSON Endpoints)
----------------------------------------
نقاط نهاية صغيرة تستدعيها الواجهة عبر JavaScript (fetch) لدعم
الإضافة السريعة للصنف/المورد من داخل الكومبوبوكس في نماذج الفواتير،
دون الحاجة لمغادرة النموذج الحالي. تُعيد استجابات JSON دائماً.
"""
from flask import Blueprint, jsonify, request

from database import get_db
from services import inventory_service
from utils.decorators import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/items/quick-add", methods=["POST"], endpoint="item_quick_add")
@login_required
def item_quick_add():
    """
    الوصف:
    تُضيف صنفاً جديداً بكمية وسعر صفر من داخل نموذج فاتورة الشراء
    عبر طلب JSON غير متزامن (AJAX)، لدعم إضافة صنف غير موجود دون
    مغادرة الفاتورة الجارية تعبئتها.

    المعاملات (في جسم الطلب JSON): item_name.
    القيمة المرجعة: JSON بالصيغة {ok, item_id, item_name} عند النجاح،
    أو {ok: False, error} برمز حالة 400 عند عدم إدخال اسم.
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("item_name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "اسم الصنف مطلوب"}), 400

    db = get_db()
    item_id = inventory_service.quick_add_item(db, name)
    db.commit()
    return jsonify({"ok": True, "item_id": item_id, "item_name": name})


@api_bp.route("/suppliers/quick-add", methods=["POST"], endpoint="supplier_quick_add")
@login_required
def supplier_quick_add():
    """
    الوصف:
    تُضيف مورداً جديداً من داخل نموذج فاتورة الشراء عبر طلب JSON غير
    متزامن (AJAX)، بنفس فكرة الإضافة السريعة للصنف أعلاه.

    المعاملات (في جسم الطلب JSON): supplier_name.
    القيمة المرجعة: JSON بالصيغة {ok, supplier_id, supplier_name} عند
    النجاح، أو {ok: False, error} برمز حالة 400 عند عدم إدخال اسم.
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("supplier_name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "اسم المورد مطلوب"}), 400

    db = get_db()
    supplier_id = inventory_service.quick_add_supplier(db, name)
    db.commit()
    return jsonify({"ok": True, "supplier_id": supplier_id, "supplier_name": name})
