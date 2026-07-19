"""utils/helpers.py — دوال مساعدة عامة"""
from datetime import date

def generate_next_document_number(db, table, column, prefix):
    """توليد رقم مستند تسلسلي فريد"""
    sequence = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] + 1
    while True:
        candidate = f"{prefix}-{date.today().year}-{sequence:04d}"
        exists = db.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (candidate,)).fetchone()
        if exists is None:
            return candidate
        sequence += 1

def aggregate_quantities_by_item(rows):
    """تجميع الكميات لنفس الصنف عبر صفوف متعددة"""
    totals = {}
    for row in rows:
        totals[row["item_id"]] = totals.get(row["item_id"], 0) + row["quantity"]
    return totals
