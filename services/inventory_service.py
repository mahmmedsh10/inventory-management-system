"""
services/inventory_service.py — خدمة المخزون
"""
from services.audit_service import log_action

def list_active_items(db):
    return db.execute("SELECT * FROM items WHERE is_active = 1 ORDER BY item_name").fetchall()

def get_active_item(db, item_id):
    return db.execute("SELECT * FROM items WHERE item_id=? AND is_active=1", (item_id,)).fetchone()

def create_item(db, name, quantity, reorder_level, purchase_price, notes, unit="قطعة"):
    cursor = db.execute("INSERT INTO items (item_name, quantity, reorder_level, purchase_price, notes, unit) VALUES (?,?,?,?,?,?)", (name, quantity, reorder_level, purchase_price, notes, unit))
    log_action("إضافة صنف", "items", cursor.lastrowid, name)
    return cursor.lastrowid

def update_item(db, item, name, reorder_level, notes, new_price, can_edit_prices, unit="قطعة"):
    if can_edit_prices and new_price is None:
        return False
    if can_edit_prices:
        db.execute("UPDATE items SET purchase_price=? WHERE item_id=?", (new_price, item["item_id"]))
    db.execute("UPDATE items SET item_name=?, reorder_level=?, notes=?, unit=?, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (name, reorder_level, notes, unit, item["item_id"]))
    log_action("تعديل صنف", "items", item["item_id"], name)
    return True

def soft_delete_item(db, item_id):
    item = db.execute("SELECT * FROM items WHERE item_id=?", (item_id,)).fetchone()
    if item is None:
        return None
    db.execute("UPDATE items SET is_active=0 WHERE item_id=?", (item_id,))
    log_action("حذف صنف", "items", item_id, item["item_name"])
    return item

def quick_add_item(db, name):
    cursor = db.execute("INSERT INTO items (item_name, quantity, reorder_level, purchase_price) VALUES (?,0,0,0)", (name,))
    log_action("إضافة سريعة لصنف", "items", cursor.lastrowid, name)
    return cursor.lastrowid

def list_active_suppliers(db):
    return db.execute("SELECT * FROM suppliers WHERE is_active=1 ORDER BY supplier_name").fetchall()

def create_supplier(db, name, phone, address):
    db.execute("INSERT INTO suppliers (supplier_name, phone, address) VALUES (?,?,?)", (name, phone, address))

def quick_add_supplier(db, name):
    cursor = db.execute("INSERT INTO suppliers (supplier_name) VALUES (?)", (name,))
    log_action("إضافة سريعة لمورد", "suppliers", cursor.lastrowid, name)
    return cursor.lastrowid

def list_active_customers(db):
    return db.execute("SELECT * FROM customers WHERE is_active=1 ORDER BY customer_name").fetchall()

def create_customer(db, name, phone, address):
    db.execute("INSERT INTO customers (customer_name, phone, address) VALUES (?,?,?)", (name, phone, address))

def fefo_deduct(db, doc_type, doc_id, item_id, quantity):
    remaining = quantity
    batches = db.execute("SELECT batch_id, quantity FROM item_batches WHERE item_id=? AND quantity > 0 ORDER BY expiry_date IS NULL, expiry_date, batch_id", (item_id,)).fetchall()
    for batch in batches:
        if remaining <= 0:
            break
        take = min(remaining, batch["quantity"])
        db.execute("UPDATE item_batches SET quantity = quantity - ? WHERE batch_id=?", (take, batch["batch_id"]))
        db.execute("INSERT INTO batch_consumptions (doc_type, doc_id, batch_id, quantity) VALUES (?,?,?,?)", (doc_type, doc_id, batch["batch_id"], take))
        remaining -= take

def restore_consumptions(db, doc_type, doc_id):
    rows = db.execute("SELECT batch_id, quantity FROM batch_consumptions WHERE doc_type=? AND doc_id=?", (doc_type, doc_id)).fetchall()
    for row in rows:
        db.execute("UPDATE item_batches SET quantity = quantity + ? WHERE batch_id=?", (row["quantity"], row["batch_id"]))
    db.execute("DELETE FROM batch_consumptions WHERE doc_type=? AND doc_id=?", (doc_type, doc_id))
