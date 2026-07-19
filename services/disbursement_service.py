"""خدمة الصرف"""
from services.audit_service import log_action
from utils.helpers import generate_next_document_number
from services import inventory_service

def list_disbursement_invoices(db):
    return db.execute("SELECT p.*, c.customer_name AS supplier_name, (SELECT COALESCE(SUM(subtotal),0) FROM disbursement_details WHERE invoice_id=p.invoice_id) AS total FROM disbursement_invoices p LEFT JOIN customers c ON c.customer_id = p.customer_id ORDER BY p.invoice_id DESC").fetchall()

def get_disbursement_form_context(db, invoice=None, details=None):
    return {"items": inventory_service.list_active_items(db), "customers": inventory_service.list_active_customers(db), "invoice": invoice, "details": details or []}

def get_disbursement_invoice_header(db, invoice_id):
    return db.execute("SELECT p.*, c.customer_name AS supplier_name, u1.full_name AS creator, u2.full_name AS approver FROM disbursement_invoices p LEFT JOIN customers c ON c.customer_id = p.customer_id LEFT JOIN users u1 ON u1.user_id = p.created_by LEFT JOIN users u2 ON u2.user_id = p.approved_by WHERE p.invoice_id = ?", (invoice_id,)).fetchone()

def get_disbursement_invoice_raw(db, invoice_id):
    return db.execute("SELECT * FROM disbursement_invoices WHERE invoice_id=?", (invoice_id,)).fetchone()

def get_disbursement_invoice_details(db, invoice_id):
    return db.execute("SELECT d.*, i.item_name, d.unit_price AS price FROM disbursement_details d JOIN items i ON i.item_id = d.item_id WHERE d.invoice_id = ?", (invoice_id,)).fetchall()

def create_draft_disbursement(db, rows, customer_id, invoice_date, notes, created_by):
    number = generate_next_document_number(db, "disbursement_invoices", "invoice_number", "DIS")
    cursor = db.execute("INSERT INTO disbursement_invoices (invoice_number, customer_id, invoice_date, notes, created_by) VALUES (?,?,?,?,?)", (number, customer_id, invoice_date, notes, created_by))
    invoice_id = cursor.lastrowid
    for r in rows:
        db.execute("INSERT INTO disbursement_details (invoice_id, item_id, quantity, unit_price) VALUES (?,?,?,?)", (invoice_id, r["item_id"], r["quantity"], r["price"]))
    log_action("إنشاء فاتورة صرف", "disbursement_invoices", invoice_id, number)
    return invoice_id, number

def update_draft_disbursement(db, invoice, rows, customer_id, invoice_date, notes):
    db.execute("UPDATE disbursement_invoices SET customer_id=?, invoice_date=?, notes=? WHERE invoice_id=?", (customer_id, invoice_date or invoice["invoice_date"], notes, invoice["invoice_id"]))
    db.execute("DELETE FROM disbursement_details WHERE invoice_id=?", (invoice["invoice_id"],))
    for r in rows:
        db.execute("INSERT INTO disbursement_details (invoice_id, item_id, quantity, unit_price) VALUES (?,?,?,?)", (invoice["invoice_id"], r["item_id"], r["quantity"], r["price"]))
    log_action("تعديل فاتورة صرف", "disbursement_invoices", invoice["invoice_id"], invoice["invoice_number"])

def approve_disbursement(db, invoice, approved_by):
    if invoice["status"] != "مسودة":
        return False, "الفاتورة ليست مسودة"
    details = db.execute("SELECT * FROM disbursement_details WHERE invoice_id=?", (invoice["invoice_id"],)).fetchall()
    if not details:
        return False, "لا يمكن اعتماد فاتورة بدون أصناف"
    from utils.helpers import aggregate_quantities_by_item
    agg = aggregate_quantities_by_item(details)
    for item_id, qty in agg.items():
        row = db.execute("SELECT item_name, quantity FROM items WHERE item_id=?", (item_id,)).fetchone()
        if row["quantity"] < qty:
            return False, f"الرصيد غير كافٍ للصنف «{row['item_name']}» (المتاح {row['quantity']} والمطلوب {qty})"
    for item_id, qty in agg.items():
        db.execute("UPDATE items SET quantity = quantity - ?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (qty, item_id))
        inventory_service.fefo_deduct(db, "صرف", invoice["invoice_id"], item_id, qty)
    db.execute("UPDATE disbursement_invoices SET status=?, approved_by=?, approved_at=CURRENT_TIMESTAMP WHERE invoice_id=?", ("معتمدة", approved_by, invoice["invoice_id"]))
    log_action("اعتماد فاتورة صرف", "disbursement_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "تم اعتماد الفاتورة وخصم الكميات من المخزون"

def unapprove_disbursement(db, invoice):
    if invoice["status"] != "معتمدة":
        return False, "الفاتورة ليست معتمدة"
    details = db.execute("SELECT * FROM disbursement_details WHERE invoice_id=?", (invoice["invoice_id"],)).fetchall()
    from utils.helpers import aggregate_quantities_by_item
    agg = aggregate_quantities_by_item(details)
    for item_id, qty in agg.items():
        db.execute("UPDATE items SET quantity = quantity + ?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (qty, item_id))
    inventory_service.restore_consumptions(db, "صرف", invoice["invoice_id"])
    db.execute("UPDATE disbursement_invoices SET status=?, approved_by=NULL, approved_at=NULL WHERE invoice_id=?", ("مسودة", invoice["invoice_id"]))
    log_action("إلغاء اعتماد فاتورة صرف", "disbursement_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "أُلغي الاعتماد وأُعيدت الكميات — الفاتورة الآن مسودة قابلة للتعديل"

def cancel_disbursement(db, invoice):
    if invoice["status"] != "مسودة":
        return False, "لا يمكن إلغاء إلا المسودات"
    db.execute("UPDATE disbursement_invoices SET status=? WHERE invoice_id=?", ("ملغاة", invoice["invoice_id"]))
    log_action("إلغاء فاتورة صرف", "disbursement_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "أُلغيت الفاتورة"
