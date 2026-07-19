# 📦 Inventory Management System
## نظام إدارة المخزون

> Professional Inventory Management System built with Flask & SQLite

---

# ✨ Features | المميزات

- 📦 Inventory Management
- 🛒 Purchase Invoices
- 📤 Issue Vouchers
- 🗑 Disposal Vouchers
- 📅 FEFO Batch Management
- 👥 User & Permission Management
- 📊 Dashboard & Statistics
- 📈 Reports
- 🔍 Audit Logs
- 🔐 Secure Authentication
- 🌍 Full Arabic Interface

---

# 🏗 Project Architecture

```
inventory_app/
│
├── app.py                 # Application Entry Point
├── config.py              # Configuration
├── database.py            # Database Layer
├── schema.sql             # Database Schema
├── requirements.txt
│
├── routes/                # Flask Blueprints
│   ├── auth.py
│   ├── dashboard.py
│   ├── items.py
│   ├── purchases.py
│   ├── reports.py
│   └── ...
│
├── services/              # Business Logic
│
├── models/
│
├── utils/
│
├── templates/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── instance/
```

---

# ⚙ Requirements

- Python 3.11+
- Flask 3.x
- SQLite

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🚀 Run

```bash
python app.py
```

Open

```
http://127.0.0.1:5000
```

---

# 👤 Default Login

| Username | Password |
|-----------|----------|
| admin | admin123 |

---

# 📂 Main Modules

## Inventory

- Add Item
- Edit Item
- Stock Balance
- Categories

## Purchasing

- Purchase Invoice
- Suppliers
- Batch Creation

## Store Issue

- Issue Voucher
- FEFO Auto Selection

## Disposal

- Disposal Voucher
- Reason Tracking

## Reports

- Current Stock
- Purchase History
- Issue History
- Expired Items
- Low Stock
- Audit Report

## Administration

- Users
- Roles
- Permissions
- System Settings

---

# 🔐 Security

- Password Hashing
- Session Protection
- CSRF Protection
- Input Validation
- Environment Variables
- Audit Logging
- Role-Based Access Control (RBAC)

---

# 🧠 FEFO System

**First Expired First Out**

When issuing inventory, the system automatically selects the batch with the nearest expiration date.

```
Batch A → Expire 10/2026
Batch B → Expire 12/2026

↓
Issue from Batch A First
```

---

# 📊 Database

Core Tables

```
users
roles
permissions

items
categories

suppliers
customers

batches

purchase_invoices
purchase_items

issue_vouchers
issue_items

disposal_vouchers
disposal_items

audit_logs
```

---

# 📈 Workflow

```
Browser

    │

    ▼

Flask Routes

    │

    ▼

Business Services

    │

    ▼

SQLite Database
```

---

# 📌 Future Roadmap

- Barcode Support
- QR Code
- Excel Import
- Excel Export
- PDF Reports
- Email Notifications
- Multi Warehouse
- REST API
- Mobile Application

---

# 📜 License

Private Project

---

# 👨‍💻 Author

Developed using

- Python
- Flask
- SQLite
- Bootstrap 5
- JavaScript

---

Version 2.0

July 2026