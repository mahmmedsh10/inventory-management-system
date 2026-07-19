"""
services/dashboard_stats_service.py
=====================================
Dashboard Statistics Service

Implements the "Dashboard Statistics" feature: a set of 7 summary
counters (Total Items, Available Items, Out of Stock Items, Total
Stock Quantity, Total Issued Quantity, Expired Items, Expiring Soon)
plus the read-only drill-down report queries behind each clickable
card.

Design notes
------------
* All figures are computed from "Approved" (معتمدة) documents only.
  Draft and Cancelled documents are excluded from every query, per
  the business rule that only approved transactions represent real
  inventory movement.
* There is no server-side caching layer here on purpose: every call
  re-runs its query against the live database, so the numbers are
  always in sync the moment a document is approved or its approval
  is reverted. This satisfies the "must automatically refresh"
  requirement without needing an event bus or background job.
* Every query is a single targeted COUNT()/SUM()/GROUP BY statement
  that only selects the columns each report needs — no SELECT * and
  no loading of unrelated rows into memory. The supporting indexes
  are created in database.py (_migrate) and schema.sql.
* "Item Code" in the UI maps to items.item_id, since the schema does
  not define a separate SKU/code field. "Unit" maps to the new
  items.unit column added specifically for this feature.
"""
from database import get_db

# Approved-status literal, matching the CHECK constraints in schema.sql
STATUS_APPROVED = "معتمدة"


# ---------------------------------------------------------------------
# 1) Summary counters (the 7 clickable cards)
# ---------------------------------------------------------------------
def get_detailed_dashboard_stats():
    """
    Compute the 7 headline dashboard statistics in a single pass of
    small, targeted queries. Each query is independently optimized
    (COUNT/SUM with WHERE/JOIN on indexed columns) rather than one
    large multi-join query, so a slow join on one metric can never
    block the others and each can be reasoned about independently.

    Returns
    -------
    dict with keys:
        total_items            : int  — active items registered
        available_items        : int  — active items with quantity > 0
        out_of_stock_items     : int  — active items with quantity = 0
        total_stock_quantity   : int  — SUM(quantity) across active items
        total_issued_quantity  : int  — SUM(quantity) from approved
                                         disbursement invoices only
        expired_items          : int  — distinct items holding stock in
                                         at least one expired batch
        expiring_soon_items    : int  — distinct items holding stock in
                                         at least one batch expiring
                                         within the next 30 days
    """
    db = get_db()

    total_items = db.execute(
        "SELECT COUNT(*) FROM items WHERE is_active = 1"
    ).fetchone()[0]

    available_items = db.execute(
        "SELECT COUNT(*) FROM items WHERE is_active = 1 AND quantity > 0"
    ).fetchone()[0]

    out_of_stock_items = db.execute(
        "SELECT COUNT(*) FROM items WHERE is_active = 1 AND quantity = 0"
    ).fetchone()[0]

    total_stock_quantity = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM items WHERE is_active = 1"
    ).fetchone()[0]

    # Only quantities from APPROVED disbursement invoices count as
    # "issued" — draft and cancelled invoices never touched stock.
    total_issued_quantity = db.execute("""
        SELECT COALESCE(SUM(dd.quantity), 0)
        FROM disbursement_details dd
        JOIN disbursement_invoices di ON di.invoice_id = dd.invoice_id
        WHERE di.status = ?
    """, (STATUS_APPROVED,)).fetchone()[0]

    # Reuse the existing v_expiry_alerts view (already indexed via
    # idx_batches_item / idx_batches_expiry) instead of duplicating
    # its expiry-classification logic here.
    expired_items = db.execute(
        "SELECT COUNT(DISTINCT item_id) FROM v_expiry_alerts WHERE expiry_status = 'منتهي الصلاحية'"
    ).fetchone()[0]

    expiring_soon_items = db.execute(
        "SELECT COUNT(DISTINCT item_id) FROM v_expiry_alerts WHERE expiry_status = 'يقترب من الانتهاء'"
    ).fetchone()[0]

    return {
        "total_items": total_items,
        "available_items": available_items,
        "out_of_stock_items": out_of_stock_items,
        "total_stock_quantity": total_stock_quantity,
        "total_issued_quantity": total_issued_quantity,
        "expired_items": expired_items,
        "expiring_soon_items": expiring_soon_items,
    }


# ---------------------------------------------------------------------
# 2) Read-only drill-down reports (one per clickable card)
# ---------------------------------------------------------------------
def get_available_items_report():
    """
    Card: "Available Items" (الأصناف المتوفرة).

    Columns: item_code, item_name, quantity, unit, nearest_expiry_date,
    stock_status.

    "nearest_expiry_date" is the soonest expiry date among the item's
    remaining batches (NULL if the item has no batch-tracked stock).
    "stock_status" flags items that are available but already at/below
    their reorder level, so low-but-nonzero stock is still visible.
    """
    return get_db().execute("""
        SELECT
            i.item_id AS item_code,
            i.item_name,
            i.quantity,
            i.unit,
            (
                SELECT MIN(b.expiry_date)
                FROM item_batches b
                WHERE b.item_id = i.item_id
                  AND b.quantity > 0
                  AND b.expiry_date IS NOT NULL
            ) AS nearest_expiry_date,
            CASE
                WHEN i.quantity <= i.reorder_level THEN 'قرب النفاد'
                ELSE 'طبيعي'
            END AS stock_status
        FROM items i
        WHERE i.is_active = 1 AND i.quantity > 0
        ORDER BY i.item_name
    """).fetchall()


def get_out_of_stock_items_report():
    """
    Card: "Out of Stock Items" (الأصناف غير المتوفرة).

    Columns: item_code, item_name, last_issue_date,
    last_available_quantity, minimum_stock_level.

    The schema keeps only the current quantity per item (no historical
    stock ledger), so "last_available_quantity" is approximated as the
    quantity moved in the item's most recent APPROVED disbursement —
    the transaction that most likely depleted it. This is documented
    here rather than silently guessed at in the template.
    """
    return get_db().execute("""
        SELECT
            i.item_id AS item_code,
            i.item_name,
            (
                SELECT MAX(di.invoice_date)
                FROM disbursement_details dd
                JOIN disbursement_invoices di ON di.invoice_id = dd.invoice_id
                WHERE dd.item_id = i.item_id AND di.status = ?
            ) AS last_issue_date,
            (
                SELECT dd.quantity
                FROM disbursement_details dd
                JOIN disbursement_invoices di ON di.invoice_id = dd.invoice_id
                WHERE dd.item_id = i.item_id AND di.status = ?
                ORDER BY di.invoice_date DESC, di.invoice_id DESC
                LIMIT 1
            ) AS last_available_quantity,
            i.reorder_level AS minimum_stock_level
        FROM items i
        WHERE i.is_active = 1 AND i.quantity = 0
        ORDER BY i.item_name
    """, (STATUS_APPROVED, STATUS_APPROVED)).fetchall()


def get_issued_items_report(sort_order="desc"):
    """
    Card: "Total Issued Quantity" (إجمالي المصروف).

    Columns: item_code, item_name, total_issued_quantity,
    issue_transactions_count, last_issue_date. Aggregated with
    SUM()/COUNT()/GROUP BY over APPROVED disbursement invoices only.

    Parameters
    ----------
    sort_order : 'desc' (default, highest issued quantity first) or
                 'asc' (lowest first), as requested by the UI's sort
                 control. Any other value falls back to 'desc'.
    """
    direction = "ASC" if sort_order == "asc" else "DESC"
    return get_db().execute(f"""
        SELECT
            i.item_id AS item_code,
            i.item_name,
            SUM(dd.quantity) AS total_issued_quantity,
            COUNT(DISTINCT di.invoice_id) AS issue_transactions_count,
            MAX(di.invoice_date) AS last_issue_date
        FROM disbursement_details dd
        JOIN disbursement_invoices di ON di.invoice_id = dd.invoice_id
        JOIN items i ON i.item_id = dd.item_id
        WHERE di.status = ?
        GROUP BY i.item_id, i.item_name
        ORDER BY total_issued_quantity {direction}
    """, (STATUS_APPROVED,)).fetchall()


def get_total_items_report():
    """
    Card: "Total Items" (إجمالي الأصناف).

    A full read-only listing of every active item with its current
    quantity, unit and reorder level, for a quick overview of the
    entire catalog behind the headline count.
    """
    return get_db().execute("""
        SELECT
            item_id AS item_code,
            item_name,
            quantity,
            unit,
            reorder_level AS minimum_stock_level,
            CASE WHEN quantity = 0 THEN 'غير متوفر' ELSE 'متوفر' END AS stock_status
        FROM items
        WHERE is_active = 1
        ORDER BY item_name
    """).fetchall()


def get_total_stock_report():
    """
    Card: "Total Stock Quantity" (إجمالي كمية المخزون).

    Same underlying data as get_total_items_report(), but ordered by
    quantity (highest first) since the card is specifically about the
    quantity figure rather than the item roster itself.
    """
    return get_db().execute("""
        SELECT
            item_id AS item_code,
            item_name,
            quantity,
            unit,
            reorder_level AS minimum_stock_level
        FROM items
        WHERE is_active = 1
        ORDER BY quantity DESC
    """).fetchall()


def get_expired_items_report():
    """
    Card: "Expired Items" (الأصناف المنتهية).

    Per-batch listing (not per-item) so the user can see exactly which
    batch is expired, its remaining quantity, and how many days
    overdue it is. Backed by the v_expiry_alerts view.
    """
    return get_db().execute("""
        SELECT
            item_id AS item_code,
            item_name,
            batch_number,
            expiry_date,
            quantity,
            ABS(days_to_expiry) AS days_overdue
        FROM v_expiry_alerts
        WHERE expiry_status = 'منتهي الصلاحية'
        ORDER BY days_to_expiry
    """).fetchall()


def get_expiring_soon_report():
    """
    Card: "Expiring Soon" (تنتهي قريباً).

    Per-batch listing of stock expiring within the next 30 days,
    backed by the v_expiry_alerts view.
    """
    return get_db().execute("""
        SELECT
            item_id AS item_code,
            item_name,
            batch_number,
            expiry_date,
            quantity,
            days_to_expiry
        FROM v_expiry_alerts
        WHERE expiry_status = 'يقترب من الانتهاء'
        ORDER BY days_to_expiry
    """).fetchall()
