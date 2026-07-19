"""
routes/dashboard.py
=====================
Main dashboard route.

Renders the overview screen (quick stat cards, low-stock alerts,
expiry alerts, top-moving items) and the "Dashboard Statistics"
feature: 7 clickable summary cards, each opening a dedicated
read-only drill-down report. None of the drill-down pages expose
any edit/delete/approve/cancel actions — they are for reporting
only, as required.
"""
from flask import Blueprint, abort, render_template, request

from services import dashboard_stats_service, report_service
from utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    """
    Render the main dashboard: quick stat cards, low-stock alerts,
    expiry alerts, total write-off losses, top-moving items, and the
    7 detailed Dashboard Statistics cards. All figures are computed
    live on every request (no caching), so they always reflect the
    latest approved/unapproved documents.
    """
    stats = report_service.get_dashboard_stats()
    low_stock = report_service.get_low_stock_alerts()
    expiry = report_service.get_expiry_alerts()
    writeoff_losses = report_service.get_total_writeoff_losses()
    top_disbursed = report_service.get_disbursement_stats()
    top_writeoff = report_service.get_writeoff_stats()
    top_movements = report_service.get_top_movements()
    detailed_stats = dashboard_stats_service.get_detailed_dashboard_stats()

    return render_template(
        "dashboard.html",
        stats=stats,
        low_stock=low_stock,
        expiry=expiry,
        writeoff_losses=writeoff_losses,
        top_disbursed=top_disbursed,
        top_writeoff=top_writeoff,
        top_movements=top_movements,
        detailed_stats=detailed_stats,
    )


# ---------------------------------------------------------------------
# Dashboard Statistics — read-only drill-down report pages
# ---------------------------------------------------------------------
# Every route below is strictly read-only: it only SELECTs data and
# renders it. There is no POST handler, no form, and no link to any
# edit/delete/approve/cancel action anywhere in these pages or their
# shared template (templates/dashboard_details/report_list.html).

@dashboard_bp.route("/dashboard/details/total-items")
@login_required
def details_total_items():
    """Read-only drill-down for the 'Total Items' card."""
    rows = dashboard_stats_service.get_total_items_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="إجمالي الأصناف",
        page_description="كل الأصناف النشطة المسجلة في النظام.",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("quantity", "الكمية الحالية"),
            ("unit", "الوحدة"),
            ("minimum_stock_level", "حد التنبيه"),
            ("stock_status", "الحالة"),
        ],
        rows=rows,
    )


@dashboard_bp.route("/dashboard/details/available-items")
@login_required
def details_available_items():
    """Read-only drill-down for the 'Available Items' card."""
    rows = dashboard_stats_service.get_available_items_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="الأصناف المتوفرة",
        page_description="الأصناف التي رصيدها الحالي أكبر من صفر.",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("quantity", "الكمية الحالية"),
            ("unit", "الوحدة"),
            ("nearest_expiry_date", "أقرب تاريخ صلاحية"),
            ("stock_status", "حالة الرصيد"),
        ],
        rows=rows,
    )


@dashboard_bp.route("/dashboard/details/out-of-stock")
@login_required
def details_out_of_stock():
    """Read-only drill-down for the 'Out of Stock Items' card."""
    rows = dashboard_stats_service.get_out_of_stock_items_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="الأصناف غير المتوفرة",
        page_description="الأصناف التي نفد رصيدها بالكامل (الكمية = صفر).",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("last_issue_date", "آخر تاريخ صرف"),
            ("last_available_quantity", "آخر كمية مصروفة"),
            ("minimum_stock_level", "حد التنبيه"),
        ],
        rows=rows,
    )


@dashboard_bp.route("/dashboard/details/total-stock")
@login_required
def details_total_stock():
    """Read-only drill-down for the 'Total Stock Quantity' card."""
    rows = dashboard_stats_service.get_total_stock_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="إجمالي كمية المخزون",
        page_description="كل الأصناف مرتبة حسب الكمية المتاحة (الأعلى أولاً).",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("quantity", "الكمية الحالية"),
            ("unit", "الوحدة"),
            ("minimum_stock_level", "حد التنبيه"),
        ],
        rows=rows,
    )


@dashboard_bp.route("/dashboard/details/issued-items")
@login_required
def details_issued_items():
    """
    Read-only drill-down for the 'Total Issued Quantity' card.
    Supports ?sort=asc|desc (defaults to desc — highest issued first).
    """
    sort_order = request.args.get("sort", "desc")
    if sort_order not in ("asc", "desc"):
        abort(400)

    rows = dashboard_stats_service.get_issued_items_report(sort_order)
    return render_template(
        "dashboard_details/report_list.html",
        page_title="إجمالي المصروف",
        page_description="الكميات المصروفة من فواتير الصرف المعتمدة فقط.",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("total_issued_quantity", "إجمالي الكمية المصروفة"),
            ("issue_transactions_count", "عدد عمليات الصرف"),
            ("last_issue_date", "آخر تاريخ صرف"),
        ],
        rows=rows,
        sortable=True,
        current_sort=sort_order,
    )


@dashboard_bp.route("/dashboard/details/expired-items")
@login_required
def details_expired_items():
    """Read-only drill-down for the 'Expired Items' card."""
    rows = dashboard_stats_service.get_expired_items_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="الأصناف المنتهية",
        page_description="دفعات لا تزال بالمخزون لكن تاريخ صلاحيتها انتهى.",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("batch_number", "رقم الدفعة"),
            ("expiry_date", "تاريخ الانتهاء"),
            ("quantity", "الكمية"),
            ("days_overdue", "أيام التأخير"),
        ],
        rows=rows,
    )


@dashboard_bp.route("/dashboard/details/expiring-soon")
@login_required
def details_expiring_soon():
    """Read-only drill-down for the 'Expiring Soon' card."""
    rows = dashboard_stats_service.get_expiring_soon_report()
    return render_template(
        "dashboard_details/report_list.html",
        page_title="تنتهي قريباً",
        page_description="دفعات ستنتهي صلاحيتها خلال 30 يوماً القادمة.",
        columns=[
            ("item_code", "رمز الصنف"),
            ("item_name", "اسم الصنف"),
            ("batch_number", "رقم الدفعة"),
            ("expiry_date", "تاريخ الانتهاء"),
            ("quantity", "الكمية"),
            ("days_to_expiry", "الأيام المتبقية"),
        ],
        rows=rows,
    )
