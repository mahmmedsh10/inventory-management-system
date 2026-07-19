"""
utils/validators.py — التحقق من صحة المدخلات
"""
from flask import request

def parse_int_field(name, default=0, minimum=0):
    """قراءة حقل صحيح من النموذج والتحقق منه"""
    try:
        value = int(request.form.get(name, default) or default)
    except (TypeError, ValueError):
        return None
    return value if value >= minimum else None

def parse_float_field(name, default=0.0, minimum=0.0):
    """قراءة حقل عشري من النموذج والتحقق منه"""
    try:
        value = float(request.form.get(name, default) or default)
    except (TypeError, ValueError):
        return None
    return value if value >= minimum else None

def parse_invoice_rows(price_field):
    """قراءة وتحقق صفوف فاتورة من النموذج"""
    item_ids = request.form.getlist("item_id[]")
    quantities = request.form.getlist("quantity[]")
    prices = request.form.getlist(price_field + "[]")
    batch_numbers = request.form.getlist("batch_number[]")
    expiry_dates = request.form.getlist("expiry_date[]")

    rows = []
    for i, item_id in enumerate(item_ids):
        item_id = (item_id or "").strip()
        if not item_id:
            continue
        try:
            qty = int(quantities[i])
            price = float(prices[i]) if i < len(prices) and prices[i] else 0.0
        except (ValueError, IndexError):
            return None, "قيم الكمية أو السعر غير صالحة"
        if qty <= 0:
            return None, "الكمية يجب أن تكون أكبر من صفر"
        if price < 0:
            return None, "السعر لا يمكن أن يكون سالباً"
        rows.append({
            "item_id": int(item_id),
            "quantity": qty,
            "price": price,
            "batch_number": (batch_numbers[i].strip() if i < len(batch_numbers) else "") or None,
            "expiry_date": (expiry_dates[i].strip() if i < len(expiry_dates) else "") or None,
        })

    if not rows:
        return None, "الفاتورة يجب أن تحتوي على صنف واحد على الأقل"
    return rows, None

def parse_writeoff_rows(db):
    """قراءة وتحقق صفوف إذن إعدام من النموذج"""
    item_ids = request.form.getlist("item_id[]")
    quantities = request.form.getlist("quantity[]")

    rows = []
    for i, item_id in enumerate(item_ids):
        item_id = (item_id or "").strip()
        if not item_id:
            continue
        try:
            qty = int(quantities[i])
        except (ValueError, IndexError):
            return None, "قيم الكمية غير صالحة"
        if qty <= 0:
            return None, "الكمية يجب أن تكون أكبر من صفر"
        item = db.execute("SELECT purchase_price FROM items WHERE item_id=?", (int(item_id),)).fetchone()
        if item is None:
            return None, "صنف غير موجود"
        rows.append({
            "item_id": int(item_id),
            "quantity": qty,
            "unit_cost": item["purchase_price"] or 0,
        })

    if not rows:
        return None, "الإذن يجب أن يحتوي على صنف واحد على الأقل"
    return rows, None
