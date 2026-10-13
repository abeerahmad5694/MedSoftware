# GeneralSoftware - Django ERP Project Documentation

This document describes the structure, architecture, and modules of the GeneralSoftware Django ERP application.

---

## 1. Project Overview
GeneralSoftware is a Django-based Enterprise Resource Planning (ERP) application designed to manage Inventory, Sales, Purchases, Ledgers, Accounts, and Quotations for multi-branch companies. 

- **Django Version**: 6.0.x
- **Database**: SQLite3 (`db.sqlite3` in the workspace root)
- **Primary Tech Stack**: Python (Django), HTML5, CSS3, JavaScript (ES6 Modules)

---



for /d %i in (apps\*) do mkdir %i\migrations form migrations folders
for /d %i in (apps\*) do type nul > %i\migrations\__init__.py   for init files in migrations folders




## 2. Core Architecture & Modules

The application is modularized into several Django apps located under the `mysite/apps/` directory:

### Core Modules:

1. **`configuration` (`apps.configuration`)**
   - Manages company-wide configurations, branches, and active settings (e.g. `Company`, `Branch` models).

2. **`inventory` (`apps.inventory`)**
   - Contains the core `Inventory` model representing products, stock tracking, categories, barcodes (including support for barcode scanning and weighted barcodes), and base/wholesale/carton pricing models.

3. **`myaccounts` (`apps.myaccounts`)**
   - Manages supplier and customer accounts, ledger mappings, and details for accounting relationships.

4. **`myledger` (`apps.myledger`)**
   - Handles the financial ledger, voucher generation (`Gledg` model), and voucher modals.

5. **`sale` (`apps.sale`)**
   - Handles Point of Sale (POS) invoices, transaction processing, receipt printing layouts, and retail/wholesale price modes.

6. **`purchase` (`apps.purchase`)**
   - Manages purchases, supplier invoices, bulk inventory intake, and landed cost calculations.
   - Computes weighted allocations of freight, labor, unload, and miscellaneous charges to arrive at the true landed cost per base unit.
   - Includes custom row registries (`window.PURCHASE_CART_ROW_FIELDS`) to support dynamic inputs like batch number or expiry dates.

7. **`quotation` (`apps.quotation`)**
   - Manages quotes and estimates (`Quotation` model), payment modes, and quote validations.

8. **`mysearch` (`apps.mysearch`)**
   - Implements a global search modal (both client-side local search and paginated server-side search) for products and accounts.

9. **`users` (`apps.users`)**
   - Extends standard Django auth with user profiles, branch restrictions, and POS terminal mappings.

10. **`myglobal` (`apps.myglobal`)**
    - Supplies global helpers, utility services, and middleware:
      - `LoginRequiredMiddleware`: Enforces site-wide authentication.
      - `AutoLogoutMiddleware`: Logs out inactive users.
      - `dynamic_js_urls`: Context processor to dynamically load static JS files into templates.

---

## 3. Notable Custom Mechanisms

### A. Dynamic Cart Row Registries
The purchase module implements a dynamic registry system allowing developers to add columns to the cart in a single place without modifying core Javascript files:
- **Registry**: Defined in `purchase.html` inline script (`window.PURCHASE_CART_ROW_FIELDS`).
- **Mechanism**: `cart.js` reads the registry to dynamically render table headers (`<thead>`) and cells (`<td>`), apply column widths, assign defaults, and handle change updates.
- **Payload Builder**: `payload.js` loops over the registry to map these custom fields to items sent in JSON payloads.

### B. Landed Cost & Inventory Valuation
During a purchase transaction, header charges (freight, labour, unload, miscellaneous) and discounts are allocated to cart items proportionally by value using `calculate_landed_cost`.
- Cost per base unit is written to the model (`row_total_cost_per_base_unit`).
- Inventory levels are updated dynamically via `handle_inventory_val()`, adjusting `bal_qty` and updating the product's `last_pur_price`.

---

## 4. Folder Structure
```
GeneralSoftware/
├── mysite/
│   ├── apps/
│   │   ├── configuration/
│   │   ├── inventory/
│   │   ├── myaccounts/
│   │   ├── myglobal/
│   │   ├── myledger/
│   │   ├── mysearch/
│   │   ├── purchase/
│   │   ├── quotation/
│   │   ├── sale/
│   │   └── users/
│   ├── mysite/            # Main project configuration (settings.py, urls.py)
│   ├── static/            # Static assets
│   ├── templates/         # Global template overrides
│   ├── manage.py
│   └── db.sqlite3
└── project.md             # This file
```
