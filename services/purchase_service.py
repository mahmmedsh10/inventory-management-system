"""
services/purchase_service.py — خدمة الشراء
"""
from services.audit_service import log_action
from utils.helpers import generate_next_document_number

def list_purchase_invoices(db):
    return db.execute("SELECT p.*, s.supplier_name, (SELECT COALESCE(SUM(subtotal),0) FROM purchase_details WHERE invoice_id=p.invoice_id) AS total FROM purchase_invoices p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id ORDER BY p.invoice_id DESC").fetchall()

def get_purchase_form_context(db, invoice=None, details=None):
    from services import inventory_service
    return {"items": inventory_service.list_active_items(db), "suppliers": inventory_service.list_active_suppliers(db), "invoice": invoice, "details": details or []}

def get_purchase_invoice_header(db, invoice_id):
    return db.execute("SELECT p.*, s.supplier_name, u1.full_name AS creator, u2.full_name AS approver FROM purchase_invoices p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id LEFT JOIN users u1 ON u1.user_id = p.created_by LEFT JOIN users u2 ON u2.user_id = p.approved_by WHERE p.invoice_id = ?", (invoice_id,)).fetchone()

def get_purchase_invoice_raw(db, invoice_id):
    return db.execute("SELECT * FROM purchase_invoices WHERE invoice_id=?", (invoice_id,)).fetchone()

def get_purchase_invoice_details(db, invoice_id):
    return db.execute("SELECT d.*, i.item_name FROM purchase_details d JOIN items i ON i.item_id = d.item_id WHERE d.invoice_id = ?", (invoice_id,)).fetchall()

def create_draft_purchase(db, rows, supplier_id, invoice_date, notes, created_by):
    number = generate_next_document_number(db, "purchase_invoices", "invoice_number", "PUR")
    cursor = db.execute("INSERT INTO purchase_invoices (invoice_number, supplier_id, invoice_date, notes, created_by) VALUES (?,?,?,?,?)", (number, supplier_id, invoice_date, notes, created_by))
    invoice_id = cursor.lastrowid
    for r in rows:
        db.execute("INSERT INTO purchase_details (invoice_id, item_id, quantity, price, batch_number, expiry_date) VALUES (?,?,?,?,?,?)", (invoice_id, r["item_id"], r["quantity"], r["price"], r["batch_number"], r["expiry_date"]))
    log_action("إنشاء فاتورة شراء", "purchase_invoices", invoice_id, number)
    return invoice_id, number

def update_draft_purchase(db, invoice, rows, supplier_id, invoice_date, notes):
    db.execute("UPDATE purchase_invoices SET supplier_id=?, invoice_date=?, notes=? WHERE invoice_id=?", (supplier_id, invoice_date or invoice["invoice_date"], notes, invoice["invoice_id"]))
    db.execute("DELETE FROM purchase_details WHERE invoice_id=?", (invoice["invoice_id"],))
    for r in rows:
        db.execute("INSERT INTO purchase_details (invoice_id, item_id, quantity, price, batch_number, expiry_date) VALUES (?,?,?,?,?,?)", (invoice["invoice_id"], r["item_id"], r["quantity"], r["price"], r["batch_number"], r["expiry_date"]))
    log_action("تعديل فاتورة شراء", "purchase_invoices", invoice["invoice_id"], invoice["invoice_number"])

def approve_purchase(db, invoice, approved_by):
    if invoice["status"] != "مسودة":
        return False, "الفاتورة ليست مسودة"
    details = db.execute("SELECT * FROM purchase_details WHERE invoice_id=?", (invoice["invoice_id"],)).fetchall()
    if not details:
        return False, "لا يمكن اعتماد فاتورة بدون أصناف"
    for d in details:
        db.execute("UPDATE items SET quantity = quantity + ?, purchase_price = ?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (d["quantity"], d["price"], d["item_id"]))
        if d["batch_number"] or d["expiry_date"]:
            db.execute("INSERT INTO item_batches (item_id, batch_number, expiry_date, quantity, purchase_price, received_date, source_invoice_id) VALUES (?,?,?,?,?,?,?)", (d["item_id"], d["batch_number"], d["expiry_date"], d["quantity"], d["price"], invoice["invoice_date"], invoice["invoice_id"]))
    db.execute("UPDATE purchase_invoices SET status=?, approved_by=?, approved_at=CURRENT_TIMESTAMP WHERE invoice_id=?", ("معتمدة", approved_by, invoice["invoice_id"]))
    log_action("اعتماد فاتورة شراء", "purchase_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "تم اعتماد الفاتورة وإضافة الكميات للمخزون"

def unapprove_purchase(db, invoice):
    if invoice["status"] != "معتمدة":
        return False, "الفاتورة ليست معتمدة"
    details = db.execute("SELECT * FROM purchase_details WHERE invoice_id=?", (invoice["invoice_id"],)).fetchall()
    from utils.helpers import aggregate_quantities_by_item
    agg = aggregate_quantities_by_item(details)
    for item_id, qty in agg.items():
        row = db.execute("SELECT item_name, quantity FROM items WHERE item_id=?", (item_id,)).fetchone()
        if row["quantity"] < qty:
            return False, f"لا يمكن إلغاء الاعتماد: جزء من كمية الصنف «{row['item_name']}» صُرف بالفعل"
    batches = db.execute("SELECT * FROM item_batches WHERE source_invoice_id=?", (invoice["invoice_id"],)).fetchall()
    for b in batches:
        original = db.execute("SELECT quantity FROM purchase_details WHERE invoice_id=? AND item_id=? AND COALESCE(batch_number,'')=COALESCE(?, '') AND COALESCE(expiry_date,'')=COALESCE(?, '')", (invoice["invoice_id"], b["item_id"], b["batch_number"], b["expiry_date"])).fetchone()
        if original and b["quantity"] < original["quantity"]:
            return False, "لا يمكن إلغاء الاعتماد: بعض دفعات هذه الفاتورة استُهلكت بالفعل"
    for item_id, qty in agg.items():
        db.execute("UPDATE items SET quantity = quantity - ?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (qty, item_id))
    db.execute("DELETE FROM item_batches WHERE source_invoice_id=?", (invoice["invoice_id"],))
    db.execute("UPDATE purchase_invoices SET status=?, approved_by=NULL, approved_at=NULL WHERE invoice_id=?", ("مسودة", invoice["invoice_id"]))
    log_action("إلغاء اعتماد فاتورة شراء", "purchase_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "أُلغي الاعتماد وسُحبت الكميات — الفاتورة الآن مسودة قابلة للتعديل"

def cancel_purchase(db, invoice):
    if invoice["status"] != "مسودة":
        return False, "لا يمكن إلغاء إلا المسودات"
    db.execute("UPDATE purchase_invoices SET status=? WHERE invoice_id=?", ("ملغاة", invoice["invoice_id"]))
    log_action("إلغاء فاتورة شراء", "purchase_invoices", invoice["invoice_id"], invoice["invoice_number"])
    return True, "أُلغيت الفاتورة"
