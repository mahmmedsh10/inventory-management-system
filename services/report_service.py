"""
services/report_service.py — خدمة التقارير
"""
from database import get_db

def get_dashboard_stats():
    db = get_db()
    return {
        "items": db.execute("SELECT COUNT(*) FROM items WHERE is_active=1").fetchone()[0],
        "purchases_draft": db.execute("SELECT COUNT(*) FROM purchase_invoices WHERE status='مسودة'").fetchone()[0],
        "disbursements_draft": db.execute("SELECT COUNT(*) FROM disbursement_invoices WHERE status='مسودة'").fetchone()[0],
        "writeoffs_draft": db.execute("SELECT COUNT(*) FROM writeoff_orders WHERE status='مسودة'").fetchone()[0],
    }

def get_low_stock_alerts():
    return get_db().execute("SELECT * FROM v_stock_alerts WHERE stock_status != 'طبيعي' ORDER BY quantity").fetchall()

def get_expiry_alerts():
    return get_db().execute("SELECT * FROM v_expiry_alerts WHERE expiry_status != 'صالح' ORDER BY days_to_expiry").fetchall()

def get_total_writeoff_losses():
    return get_db().execute("SELECT COALESCE(SUM(d.subtotal), 0) AS total FROM writeoff_details d JOIN writeoff_orders o ON o.writeoff_id = d.writeoff_id WHERE o.status = 'معتمدة'").fetchone()["total"]


def get_disbursement_stats():
    """
    الوصف:
    تجلب إحصائيات الأصناف المصروفة: الكميات الإجمالية والقيم المالية
    والعدد الإجمالي لفواتير الصرف لكل صنف، مرتبة من الأكثر صرفاً للأقل.
    تُستخدم هذه البيانات في لوحة التحكم لعرض أعلى الأصناف المصروفة.

    المعاملات: لا يوجد.
    القيمة المرجعة: قائمة صفوف sqlite3.Row من v_disbursement_stats.
    """
    return get_db().execute(
        "SELECT * FROM v_disbursement_stats WHERE total_disbursed_qty > 0 ORDER BY total_disbursed_qty DESC LIMIT 10"
    ).fetchall()


def get_writeoff_stats():
    """
    الوصف:
    تجلب إحصائيات أذونات الإعدام: الكميات الإجمالية المُعدَّمة والقيم المالية
    والعدد الإجمالي لأذونات الإعدام المعتمدة لكل صنف، مرتبة من الأكثر إعداماً.

    المعاملات: لا يوجد.
    القيمة المرجعة: قائمة صفوف sqlite3.Row مع إحصائيات الإعدام.
    """
    return get_db().execute("""
        SELECT 
            i.item_id,
            i.item_name,
            SUM(wd.quantity) AS total_writeoff_qty,
            SUM(wd.subtotal) AS total_writeoff_value,
            COUNT(DISTINCT wo.writeoff_id) AS writeoff_count
        FROM items i
        LEFT JOIN writeoff_details wd ON wd.item_id = i.item_id
        LEFT JOIN writeoff_orders wo ON wo.writeoff_id = wd.writeoff_id AND wo.status = 'معتمدة'
        WHERE i.is_active = 1
        GROUP BY i.item_id, i.item_name
        HAVING SUM(wd.quantity) > 0
        ORDER BY total_writeoff_qty DESC
        LIMIT 10
    """).fetchall()


def get_top_movements():
    """
    الوصف:
    تجلب أكثر الأصناف حركة (شراء + صرف) في خلال فترة معينة.
    يُستخدم لعرض رؤية عامة عن أكثر الأصناف المهمة في المخزون.

    المعاملات: لا يوجد.
    القيمة المرجعة: قائمة صفوف sqlite3.Row.
    """
    return get_db().execute("""
        SELECT 
            i.item_id,
            i.item_name,
            COALESCE(SUM(CASE WHEN pd.detail_id IS NOT NULL THEN pd.quantity ELSE 0 END), 0) AS purchased_qty,
            COALESCE(SUM(CASE WHEN dd.detail_id IS NOT NULL THEN dd.quantity ELSE 0 END), 0) AS disbursed_qty,
            i.quantity AS current_stock
        FROM items i
        LEFT JOIN purchase_details pd ON pd.item_id = i.item_id
        LEFT JOIN purchase_invoices pi ON pi.invoice_id = pd.invoice_id AND pi.status = 'معتمدة'
        LEFT JOIN disbursement_details dd ON dd.item_id = i.item_id
        LEFT JOIN disbursement_invoices di ON di.invoice_id = dd.invoice_id AND di.status = 'معتمدة'
        WHERE i.is_active = 1
        GROUP BY i.item_id, i.item_name, i.quantity
        ORDER BY (COALESCE(SUM(CASE WHEN pd.detail_id IS NOT NULL THEN pd.quantity ELSE 0 END), 0) + 
                  COALESCE(SUM(CASE WHEN dd.detail_id IS NOT NULL THEN dd.quantity ELSE 0 END), 0)) DESC
        LIMIT 10
    """).fetchall()
