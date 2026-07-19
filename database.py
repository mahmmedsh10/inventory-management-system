"""
database.py
============
طبقة الاتصال بقاعدة البيانات (Database Layer)
------------------------------------------------
هذا الملف مسؤول حصرياً عن التعامل مع اتصال SQLite: فتحه، إغلاقه،
إنشاء الجداول لأول مرة، وترحيل (migrate) قواعد البيانات القديمة إلى
البنية الحالية دون فقدان أي بيانات.

فصل هذه المسؤولية في ملف مستقل يجعل منطق الأعمال (services) ومسارات
الطلبات (routes) خاليَين تماماً من تفاصيل الاتصال بقاعدة البيانات.
"""
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    """
    الوصف:
    تعيد اتصال قاعدة بيانات SQLite الخاص بالطلب الحالي (request)،
    وتُنشئ اتصالاً جديداً إذا لم يكن موجوداً بعد داخل كائن `g`
    (وهو كائن يُنشئه Flask لكل طلب على حدة، فيضمن اتصالاً واحداً فقط
    لكل طلب بدل فتح اتصال جديد مع كل استعلام — تحسين للأداء).
    كما تُفعّل قيود المفاتيح الأجنبية (PRAGMA foreign_keys) لضمان
    تكامل البيانات بين الجداول المترابطة.

    المعاملات: لا يوجد.

    القيمة المرجعة:
    كائن اتصال sqlite3.Connection جاهز للاستخدام، بحيث تُعاد الصفوف
    ككائنات sqlite3.Row (يمكن الوصول لأعمدتها بالاسم مثل row['item_id']).
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    """
    الوصف:
    تُغلق اتصال قاعدة البيانات الخاص بالطلب الحالي إن كان مفتوحاً.
    يستدعيها Flask تلقائياً بعد الانتهاء من معالجة كل طلب
    (مسجَّلة عبر app.teardown_appcontext في register_db).

    المعاملات:
    exception: الاستثناء الذي قد يكون حدث أثناء معالجة الطلب (إن وجد).

    القيمة المرجعة: لا يوجد.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def register_db(app):
    """
    الوصف:
    تربط دالة إغلاق قاعدة البيانات (close_db) بدورة حياة تطبيق Flask
    بحيث يتم إغلاق الاتصال تلقائياً بعد كل طلب مهما كانت نتيجته.
    تُستدعى مرة واحدة عند إنشاء التطبيق في app.py.

    المعاملات:
    app: كائن تطبيق Flask.

    القيمة المرجعة: لا يوجد.
    """
    app.teardown_appcontext(close_db)


def init_db(app):
    """
    الوصف:
    تهيئة قاعدة البيانات عند إقلاع التطبيق:
    1) إنشاء الجداول من schema.sql إذا كانت قاعدة البيانات غير موجودة أصلاً.
    2) تنفيذ عمليات الترحيل (migrations) اللازمة لتحديث قواعد بيانات
       النسخ الأقدم إلى البنية الحالية دون حذف أي بيانات موجودة.
    3) إنشاء حساب المدير الافتراضي إذا كانت قاعدة البيانات فارغة تماماً
       من المستخدمين.

    المعاملات:
    app: كائن تطبيق Flask (تُقرأ منه إعدادات DB_PATH و SCHEMA_PATH).

    القيمة المرجعة: لا يوجد.
    """
    db_path = app.config["DB_PATH"]
    schema_path = app.config["SCHEMA_PATH"]

    db_path.parent.mkdir(exist_ok=True)
    is_new = not db_path.exists()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    if is_new:
        with open(schema_path, encoding="utf-8") as f:
            conn.executescript(f.read())

    _migrate(conn)
    _seed_admin(conn)

    conn.commit()
    conn.close()


def _migrate(conn):
    """
    الوصف:
    ترحيل قواعد البيانات المُنشأة بنسخ أقدم من التطبيق إلى البنية
    الحالية، بشكل آمن ومتكرر (idempotent) — أي يمكن استدعاؤها أكثر
    من مرة دون أي أثر جانبي إذا كانت قاعدة البيانات محدَّثة بالفعل.

    خطوات الترحيل:
    - حذف عمود/جدول التصنيفات (categories) من النسخ القديمة التي
      كانت تدعم تصنيف الأصناف، لأن النسخة الحالية لا تستخدم تصنيفات.
    - إضافة عمود source_invoice_id لجدول item_batches إن لم يكن موجوداً
      (يُستخدم لربط الدفعة بفاتورة الشراء التي أنشأتها، لدعم إلغاء الاعتماد).
    - إنشاء جداول أذونات الإعدام (writeoff_orders / writeoff_details)
      إذا لم تكن موجودة.
    - إنشاء جدول تتبع استهلاك الدفعات (batch_consumptions) إذا لم يكن
      موجوداً، وهو الجدول الذي يسجّل كل خصم من دفعة بسبب صرف أو إعدام
      لإتاحة التراجع الدقيق عند إلغاء الاعتماد.
    - إضافة أعمدة صلاحيات الأدوار الجديدة (can_unapprove_invoices،
      can_approve_writeoffs) وتحديث القيم الافتراضية لها حسب الدور.

    المعاملات:
    conn: اتصال sqlite3.Connection مفتوح على قاعدة البيانات.

    القيمة المرجعة: لا يوجد.
    """
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    # --- حذف التصنيفات من النسخ القديمة ---
    item_columns = [row[1] for row in conn.execute("PRAGMA table_info(items)")]
    if "category_id" in item_columns:
        conn.execute("ALTER TABLE items DROP COLUMN category_id")
    if "categories" in tables:
        conn.execute("DROP TABLE categories")

    # --- عمود ربط الدفعة بفاتورة الشراء المصدر ---
    batch_columns = [row[1] for row in conn.execute("PRAGMA table_info(item_batches)")]
    if "source_invoice_id" not in batch_columns:
        conn.execute("ALTER TABLE item_batches ADD COLUMN source_invoice_id INTEGER")

    # --- جداول أذونات الإعدام (Write-Off) ---
    if "writeoff_orders" not in tables:
        conn.executescript("""
        CREATE TABLE writeoff_orders (
            writeoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            writeoff_date DATE DEFAULT CURRENT_DATE,
            reason TEXT NOT NULL CHECK (reason IN ('منتهي الصلاحية','تالف','عجز جرد','أخرى')),
            status TEXT NOT NULL DEFAULT 'مسودة' CHECK (status IN ('مسودة','معتمدة','ملغاة')),
            notes TEXT,
            created_by INTEGER REFERENCES users(user_id),
            approved_by INTEGER REFERENCES users(user_id),
            approved_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE writeoff_details (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            writeoff_id INTEGER NOT NULL REFERENCES writeoff_orders(writeoff_id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(item_id),
            batch_id INTEGER REFERENCES item_batches(batch_id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_cost REAL NOT NULL DEFAULT 0,
            subtotal REAL GENERATED ALWAYS AS (quantity * unit_cost) STORED
        );
        """)

    # --- جدول تتبع استهلاك الدفعات (لإلغاء الاعتماد بدقة) ---
    if "batch_consumptions" not in tables:
        conn.executescript("""
        CREATE TABLE batch_consumptions (
            consumption_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL CHECK (doc_type IN ('صرف','إعدام')),
            doc_id INTEGER NOT NULL,
            batch_id INTEGER NOT NULL REFERENCES item_batches(batch_id),
            quantity INTEGER NOT NULL
        );
        """)

    # --- أعمدة صلاحيات جديدة على جدول الأدوار ---
    role_columns = [row[1] for row in conn.execute("PRAGMA table_info(roles)")]
    for column in ("can_unapprove_invoices", "can_approve_writeoffs"):
        if column not in role_columns:
            conn.execute(f"ALTER TABLE roles ADD COLUMN {column} INTEGER DEFAULT 0")

    # تحديث صلاحيات الأدوار الافتراضية بعد إضافة الأعمدة الجديدة
    conn.execute(
        "UPDATE roles SET can_unapprove_invoices=1, can_approve_writeoffs=1 "
        "WHERE role_name='مدير'"
    )
    conn.execute(
        "UPDATE roles SET can_unapprove_invoices=1, can_approve_writeoffs=0 "
        "WHERE role_name='أمين مخزن'"
    )

    # ------------------------------------------------------------------
    # Dashboard Statistics feature migration
    # ------------------------------------------------------------------
    # 'unit' column: the items table did not track a unit of measure.
    # The dashboard "Available Items" detail report requires displaying
    # the unit, so we add it here with a sensible default ('قطعة' = piece)
    # instead of leaving it NULL for every pre-existing item.
    item_columns = [row[1] for row in conn.execute("PRAGMA table_info(items)")]
    if "unit" not in item_columns:
        conn.execute("ALTER TABLE items ADD COLUMN unit TEXT NOT NULL DEFAULT 'قطعة'")

    # Performance indexes: the dashboard statistics run several
    # aggregate queries filtered by document status (only 'معتمدة'
    # documents count) and by item_id for issued-quantity rollups.
    # These indexes keep those queries fast even as invoice volume
    # grows, without loading unnecessary rows into memory.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchase_invoices_status "
        "ON purchase_invoices(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_disbursement_invoices_status "
        "ON disbursement_invoices(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_writeoff_orders_status "
        "ON writeoff_orders(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_disbursement_details_item "
        "ON disbursement_details(item_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_quantity "
        "ON items(quantity)"
    )


def _seed_admin(conn):
    """
    الوصف:
    إنشاء حساب مدير افتراضي (admin / admin123) إذا كانت قاعدة البيانات
    خالية تماماً من المستخدمين، حتى يتمكن أول مستخدم من الدخول للنظام
    وإنشاء بقية الحسابات.

    المعاملات:
    conn: اتصال sqlite3.Connection مفتوح على قاعدة البيانات.

    القيمة المرجعة: لا يوجد.
    """
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        role_id = conn.execute(
            "SELECT role_id FROM roles WHERE role_name='مدير'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO users (username, full_name, password_hash, role_id) "
            "VALUES (?,?,?,?)",
            ("admin", "مدير النظام", generate_password_hash("admin123"), role_id),
        )
