"""خدمة الإعدام"""
from services.audit_service import log_action
from utils.helpers import generate_next_document_number
from services import inventory_service

def list_writeoff_orders(db):
    return db.execute("SELECT w.*, (SELECT COALESCE(SUM(subtotal),0) FROM writeoff_details WHERE writeoff_id=w.writeoff_id) AS total FROM writeoff_orders w ORDER BY w.writeoff_id DESC").fetchall()

def get_writeoff_form_context(db, order=None, details=None, prefill=None):
    from utils.constants import WRITEOFF_REASONS
    return {"items": inventory_service.list_active_items(db), "reasons": WRITEOFF_REASONS, "order": order, "details": details or [], "prefill": prefill}

def get_writeoff_prefill(db, item_id, quantity, reason):
    item = inventory_service.get_active_item(db, item_id)
    if item is None:
        return None
    return {"item_id": item["item_id"], "item_name": item["item_name"], "qty": quantity, "reason": reason}

def get_writeoff_order_header(db, writeoff_id):
    return db.execute("SELECT w.*, u1.full_name AS creator, u2.full_name AS approver FROM writeoff_orders w LEFT JOIN users u1 ON u1.user_id = w.created_by LEFT JOIN users u2 ON u2.user_id = w.approved_by WHERE w.writeoff_id = ?", (writeoff_id,)).fetchone()

def get_writeoff_order_raw(db, writeoff_id):
    return db.execute("SELECT * FROM writeoff_orders WHERE writeoff_id=?", (writeoff_id,)).fetchone()

def get_writeoff_order_details(db, writeoff_id):
    return db.execute("SELECT d.*, i.item_name FROM writeoff_details d JOIN items i ON i.item_id = d.item_id WHERE d.writeoff_id = ?", (writeoff_id,)).fetchall()

def create_draft_writeoff(db, rows, reason, writeoff_date, notes, created_by):
    number = generate_next_document_number(db, "writeoff_orders", "order_number", "WRO")
    cursor = db.execute("INSERT INTO writeoff_orders (order_number, writeoff_date, reason, notes, created_by) VALUES (?,?,?,?,?)", (number, writeoff_date, reason, notes, created_by))
    writeoff_id = cursor.lastrowid
    for r in rows:
        db.execute("INSERT INTO writeoff_details (writeoff_id, item_id, quantity, unit_cost) VALUES (?,?,?,?)", (writeoff_id, r["item_id"], r["quantity"], r["unit_cost"]))
    log_action("إنشاء إذن إعدام", "writeoff_orders", writeoff_id, number)
    return writeoff_id, number

def update_draft_writeoff(db, order, rows, reason, writeoff_date, notes):
    db.execute("UPDATE writeoff_orders SET writeoff_date=?, reason=?, notes=? WHERE writeoff_id=?", (writeoff_date or order["writeoff_date"], reason, notes, order["writeoff_id"]))
    db.execute("DELETE FROM writeoff_details WHERE writeoff_id=?", (order["writeoff_id"],))
    for r in rows:
        db.execute("INSERT INTO writeoff_details (writeoff_id, item_id, quantity, unit_cost) VALUES (?,?,?,?)", (order["writeoff_id"], r["item_id"], r["quantity"], r["unit_cost"]))
    log_action("تعديل إذن إعدام", "writeoff_orders", order["writeoff_id"], order["order_number"])

def approve_writeoff(db, order, approved_by):
    if order["status"] != "مسودة":
        return False, "الإذن ليس مسودة"
    details = db.execute("SELECT * FROM writeoff_details WHERE writeoff_id=?", (order["writeoff_id"],)).fetchall()
    if not details:
        return False, "لا يمكن اعتماد إذن بدون أصناف"
    from utils.helpers import aggregate_quantities_by_item
    agg = aggregate_quantities_by_item(details)
    for item_id, qty in agg.items():
        row = db.execute("SELECT item_name, quantity FROM items WHERE item_id=?", (item_id,)).fetchone()
        if row["quantity"] < qty:
            return False, f"الرصيد غير كافٍ لإعدام الصنف «{row['item_name']}» (المتاح {row['quantity']} والمطلوب {qty})"
    for item_id, qty in agg.items():
        db.execute("UPDATE items SET quantity = quantity - ?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (qty, item_id))
        inventory_service.fefo_deduct(db, "إعدام", order["writeoff_id"], item_id, qty)
    db.execute("UPDATE writeoff_orders SET status=?, approved_by=?, approved_at=CURRENT_TIMESTAMP WHERE writeoff_id=?", ("معتمدة", approved_by, order["writeoff_id"]))
    log_action("اعتماد إذن إعدام", "writeoff_orders", order["writeoff_id"], order["order_number"])
    return True, "اعتُمد الإذن وخُصمت الكميات — الإعدام المعتمد نهائي ولا يمكن التراجع عنه"

def cancel_writeoff(db, order):
    if order["status"] != "مسودة":
        return False, "لا يمكن إلغاء إلا المسودات"
    db.execute("UPDATE writeoff_orders SET status=? WHERE writeoff_id=?", ("ملغاة", order["writeoff_id"]))
    log_action("إلغاء إذن إعدام", "writeoff_orders", order["writeoff_id"], order["order_number"])
    return True, "أُلغي الإذن"
