-- ============================================================
-- نظام إدارة المخزون - Schema النسخة النهائية
-- بدون تصنيفات + أذونات إعدام + تتبع استهلاك الدفعات
-- ============================================================

-- ============================================================
-- 1) الأدوار والصلاحيات
-- ============================================================
CREATE TABLE roles (
    role_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name                   TEXT NOT NULL UNIQUE,
    can_edit_prices             INTEGER DEFAULT 0,
    can_delete_items            INTEGER DEFAULT 0,
    can_approve_purchases       INTEGER DEFAULT 0,
    can_approve_disbursements   INTEGER DEFAULT 0,
    can_unapprove_invoices      INTEGER DEFAULT 0,  -- إلغاء اعتماد الفواتير المعتمدة لتعديلها
    can_approve_writeoffs       INTEGER DEFAULT 0,  -- اعتماد أذونات الإعدام
    can_manage_users            INTEGER DEFAULT 0
);

INSERT INTO roles (role_name, can_edit_prices, can_delete_items, can_approve_purchases,
                   can_approve_disbursements, can_unapprove_invoices, can_approve_writeoffs, can_manage_users)
VALUES
    ('مدير',       1, 1, 1, 1, 1, 1, 1),
    ('أمين مخزن',  1, 0, 1, 1, 1, 0, 0),
    ('موظف',       0, 0, 0, 1, 0, 0, 0);

-- ============================================================
-- 2) المستخدمون
-- ============================================================
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role_id         INTEGER NOT NULL REFERENCES roles(role_id),
    is_active       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 3) الأصناف (بدون تصنيفات)
-- ============================================================
CREATE TABLE items (
    item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name       TEXT NOT NULL,

    quantity        INTEGER NOT NULL DEFAULT 0,
    reorder_level   INTEGER DEFAULT 0,           -- حد التنبيه بالنفاد
    unit            TEXT NOT NULL DEFAULT 'قطعة', -- unit of measure (Dashboard Statistics feature)

    purchase_price  REAL DEFAULT 0,   -- آخر سعر شراء (يتحدث تلقائياً من آخر فاتورة شراء معتمدة)

    notes           TEXT,
    is_active       INTEGER DEFAULT 1, -- حذف ناعم بدل الحذف الفعلي

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 4) دفعات/تشغيلات الأصناف (تواريخ الصلاحية)
-- ============================================================
CREATE TABLE item_batches (
    batch_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id             INTEGER NOT NULL REFERENCES items(item_id),
    batch_number        TEXT,
    expiry_date         DATE,
    quantity            INTEGER NOT NULL DEFAULT 0,  -- الكمية المتبقية من هذه الدفعة
    purchase_price      REAL,
    received_date       DATE DEFAULT CURRENT_DATE,
    source_invoice_id   INTEGER,   -- فاتورة الشراء التي أنشأت الدفعة (لإلغاء الاعتماد)
    notes               TEXT
);

CREATE INDEX idx_batches_item   ON item_batches(item_id);
CREATE INDEX idx_batches_expiry ON item_batches(expiry_date);
CREATE INDEX idx_batches_source ON item_batches(source_invoice_id);

-- ============================================================
-- 5) الموردون
-- ============================================================
CREATE TABLE suppliers (
    supplier_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name   TEXT NOT NULL,
    phone           TEXT,
    address         TEXT,
    is_active       INTEGER DEFAULT 1
);

-- ============================================================
-- 6) العملاء / الجهات المستفيدة
-- ============================================================
CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name   TEXT NOT NULL,
    phone           TEXT,
    address         TEXT,
    is_active       INTEGER DEFAULT 1
);

-- ============================================================
-- 7) فواتير الشراء (رأس + تفاصيل)
-- ============================================================
CREATE TABLE purchase_invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT NOT NULL UNIQUE,
    supplier_id     INTEGER REFERENCES suppliers(supplier_id),
    invoice_date    DATE DEFAULT CURRENT_DATE,
    status          TEXT NOT NULL DEFAULT 'مسودة'
                    CHECK (status IN ('مسودة', 'معتمدة', 'ملغاة')),
    notes           TEXT,
    created_by      INTEGER REFERENCES users(user_id),
    approved_by     INTEGER REFERENCES users(user_id),
    approved_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_details (
    detail_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES purchase_invoices(invoice_id) ON DELETE CASCADE,
    item_id         INTEGER NOT NULL REFERENCES items(item_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    price           REAL NOT NULL DEFAULT 0 CHECK (price >= 0),
    batch_number    TEXT,
    expiry_date     DATE,
    subtotal        REAL GENERATED ALWAYS AS (quantity * price) STORED
);

CREATE INDEX idx_pd_invoice ON purchase_details(invoice_id);

-- ============================================================
-- 8) فواتير الصرف (رأس + تفاصيل)
-- ============================================================
CREATE TABLE disbursement_invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT NOT NULL UNIQUE,
    customer_id     INTEGER REFERENCES customers(customer_id),
    invoice_date    DATE DEFAULT CURRENT_DATE,
    status          TEXT NOT NULL DEFAULT 'مسودة'
                    CHECK (status IN ('مسودة', 'معتمدة', 'ملغاة')),
    notes           TEXT,
    created_by      INTEGER REFERENCES users(user_id),
    approved_by     INTEGER REFERENCES users(user_id),
    approved_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE disbursement_details (
    detail_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES disbursement_invoices(invoice_id) ON DELETE CASCADE,
    item_id         INTEGER NOT NULL REFERENCES items(item_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      REAL NOT NULL DEFAULT 0,
    subtotal        REAL GENERATED ALWAYS AS (quantity * unit_price) STORED
);

CREATE INDEX idx_dd_invoice ON disbursement_details(invoice_id);

-- ============================================================
-- 9) أذونات الإعدام (Write-Off) — للأصناف المنتهية/التالفة
-- ============================================================
CREATE TABLE writeoff_orders (
    writeoff_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number    TEXT NOT NULL UNIQUE,
    writeoff_date   DATE DEFAULT CURRENT_DATE,
    reason          TEXT NOT NULL
                    CHECK (reason IN ('منتهي الصلاحية', 'تالف', 'عجز جرد', 'أخرى')),
    status          TEXT NOT NULL DEFAULT 'مسودة'
                    CHECK (status IN ('مسودة', 'معتمدة', 'ملغاة')),
    notes           TEXT,
    created_by      INTEGER REFERENCES users(user_id),
    approved_by     INTEGER REFERENCES users(user_id),
    approved_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE writeoff_details (
    detail_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    writeoff_id     INTEGER NOT NULL REFERENCES writeoff_orders(writeoff_id) ON DELETE CASCADE,
    item_id         INTEGER NOT NULL REFERENCES items(item_id),
    batch_id        INTEGER REFERENCES item_batches(batch_id),  -- اختياري: دفعة محددة
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost       REAL NOT NULL DEFAULT 0,   -- تكلفة الوحدة (لتقرير الخسائر)
    subtotal        REAL GENERATED ALWAYS AS (quantity * unit_cost) STORED
);

CREATE INDEX idx_wd_order ON writeoff_details(writeoff_id);

-- ============================================================
-- 10) تتبع استهلاك الدفعات (لإلغاء الاعتماد بدقة)
--     كل خصم من دفعة بسبب صرف أو إعدام يسجَّل هنا
-- ============================================================
CREATE TABLE batch_consumptions (
    consumption_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('صرف', 'إعدام')),
    doc_id          INTEGER NOT NULL,   -- invoice_id أو writeoff_id
    batch_id        INTEGER NOT NULL REFERENCES item_batches(batch_id),
    quantity        INTEGER NOT NULL
);

CREATE INDEX idx_bc_doc ON batch_consumptions(doc_type, doc_id);

-- ============================================================
-- Dashboard Statistics feature: performance indexes
-- Speed up status-filtered aggregate queries (COUNT/SUM by
-- 'معتمدة' status) and item-level issued-quantity rollups.
-- ============================================================
CREATE INDEX idx_purchase_invoices_status ON purchase_invoices(status);
CREATE INDEX idx_disbursement_invoices_status ON disbursement_invoices(status);
CREATE INDEX idx_writeoff_orders_status ON writeoff_orders(status);
CREATE INDEX idx_disbursement_details_item ON disbursement_details(item_id);
CREATE INDEX idx_items_quantity ON items(quantity);

-- ============================================================
-- 11) سجل التدقيق
-- ============================================================
CREATE TABLE audit_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(user_id),
    action          TEXT NOT NULL,
    entity          TEXT,
    entity_id       INTEGER,
    details         TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Views للتنبيهات
-- ============================================================
CREATE VIEW v_stock_alerts AS
SELECT
    item_id, item_name, quantity, reorder_level,
    CASE
        WHEN quantity <= 0 THEN 'نفاد'
        WHEN quantity <= reorder_level THEN 'قرب النفاد'
        ELSE 'طبيعي'
    END AS stock_status
FROM items
WHERE is_active = 1;

CREATE VIEW v_expiry_alerts AS
SELECT
    b.batch_id, i.item_id, i.item_name, b.batch_number, b.quantity, b.expiry_date,
    CAST(julianday(b.expiry_date) - julianday('now') AS INTEGER) AS days_to_expiry,
    CASE
        WHEN julianday(b.expiry_date) - julianday('now') < 0 THEN 'منتهي الصلاحية'
        WHEN julianday(b.expiry_date) - julianday('now') <= 30 THEN 'يقترب من الانتهاء'
        ELSE 'صالح'
    END AS expiry_status
FROM item_batches b
JOIN items i ON i.item_id = b.item_id
WHERE b.expiry_date IS NOT NULL
  AND b.quantity > 0
  AND i.is_active = 1;

-- ========================================================
-- View: v_disbursement_stats
-- الوصف: إحصائيات الأصناف المصروفة (الكميات والقيم)
-- ========================================================
CREATE VIEW IF NOT EXISTS v_disbursement_stats AS
SELECT 
    i.item_id,
    i.item_name,
    SUM(dd.quantity) AS total_disbursed_qty,
    SUM(dd.quantity * dd.unit_price) AS total_disbursed_value,
    COUNT(DISTINCT d.invoice_id) AS disbursement_count
FROM items i
LEFT JOIN disbursement_details dd ON dd.item_id = i.item_id
LEFT JOIN disbursement_invoices d ON d.invoice_id = dd.invoice_id AND d.status = 'معتمدة'
WHERE i.is_active = 1
GROUP BY i.item_id, i.item_name
ORDER BY total_disbursed_qty DESC;

