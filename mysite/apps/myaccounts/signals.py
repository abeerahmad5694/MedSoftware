


from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.myaccounts.models import Accounts

DEFAULT_ACCOUNTS = [

    # =====================================================
    # LEVEL 1
    # =====================================================

    (1,   1, 1, 'Group', 'Assets',     'ASSETS'),
    (2,  10, 1, 'Group', 'Liability',  'LIABILITIES'),
    (3,  20, 1, 'Group', 'Expense',    'EXPENSES'),
    (4,  30, 1, 'Group', 'Income',     'REVENUE'),

    # =====================================================
    # ASSETS
    # =====================================================

    # LEVEL 2
    (11,  2, 2, 'Group', 'Assets', 'CURRENT ASSETS'),
    (12,  3, 2, 'Group', 'Assets', 'FIXED ASSETS'),

    # LEVEL 3
    (110, 4, 3, 'Group', 'Assets', 'CASH'),
    (111, 5, 3, 'Group', 'Assets', 'BANK BALANCES'),
    (112, 6, 3, 'Group', 'Asset',  'ACCOUNTS RECEIVABLES'),
    (117, 7, 3, 'Group', 'Asset',  'RAW MATERIAL/STOCK/INVENTORY'),
    (118, 8, 3, 'Group', 'Assets', 'FINISHED PRODUCT'),
    (121, 9, 3, 'Group', 'Assets', 'FIXED ASSETS'),

    #level 4
    (110000001, 10, 4, 'Detail', 'Asset', 'CASH BOOK'),
    (111000001, 11, 4, 'Detail', 'Asset', 'BANK'),
    (112000001, 12, 4, 'Detail', 'Asset', 'CASH CLIENT'),
    # (117000001, 13, 4, 'Detail', 'Asset', 'RAW MATERIAL/STOCK/INVENTORY'),
    # (118000001, 14, 4, 'Detail', 'Asset', 'FINISHED PRODUCT'),
    # (121000001, 15, 4, 'Detail', 'Asset', 'FIXED ASSETS'),

    # =====================================================
    # LIABILITIES
    # =====================================================

    # LEVEL 2
    (21, 11, 2, 'Group', 'Liability', 'EQUITY'),
    (22, 12, 2, 'Group', 'Liability', 'WITHDRAWALS'),
    (23, 13, 2, 'Group', 'Liability', 'CURRENT LIABILITIES'),

    # LEVEL 3
    (211, 14, 3, 'Group', 'Liability', 'CAPITAL'),
    (231, 15, 3, 'Group', 'Liability', 'ACCOUNTS PAYABLE'),
    (232, 16, 3, 'Group', 'Liability', 'WAGES/LABOUR PAYABLE'),
    (233, 17, 3, 'Group', 'Liability', 'FREIGHT PAYABLE'),

    # level 4
    (231000001, 18, 4, 'Detail', 'Liability', 'OPENING STOCK'),
    (232000001, 19, 4, 'Detail', 'Liability', 'LABOUR'),
    (233000001, 20, 4, 'Detail', 'Liability', 'CARRIAGE'),
    
    


    # =====================================================
    # EXPENSES
    # =====================================================

    # LEVEL 2
    (31, 21, 2, 'Group', 'Expense', 'COST OF GOODS SOLD'),
    (32, 22, 2, 'Group', 'Expense', 'PRODUCTION & SELLING EXPENSES'),
    (33, 23, 2, 'Group', 'Expense', 'ADMINISTRATIVE EXPENSES'),
    (34, 24, 2, 'Group', 'Expense', 'FINANCIAL EXPENSES'),

    # LEVEL 3
    (311, 25, 3, 'Group', 'Expense', 'COST OF SALES'),
    (321, 26, 3, 'Group', 'Expense', 'WAGES/LABOUR CHARGES'),
    (322, 27, 3, 'Group', 'Expense', 'PACKING EXPENSES'),

    # level 4
    (311000001, 28, 4, 'Detail', 'Expense', 'COST OF SALES'),
    # =====================================================
    # INCOME
    # =====================================================

    # LEVEL 2
    (41, 31, 2, 'Group', 'Income', 'REVENUE (SALES)'),
    (42, 32, 2, 'Group', 'Income', 'TRANSPORTATION INCOME'),
    (43, 33, 2, 'Group', 'Income', 'OTHER INCOME'),

    # LEVEL 3
    (411, 34, 3, 'Group', 'Income', 'SALES'),

]
@receiver(post_migrate)
def create_default_accounts(sender, **kwargs):
    if sender.name != 'apps.myaccounts':
        return

    print("\n[Accounts Initialization] Checking...")

    # ---------------------------------------------------------
    # 1. Ensure organizational data exists - BUT DON'T OVERWRITE
    # ---------------------------------------------------------
    from apps.configuration.models import Company, Branch, POSTerminal, CompanyConfiguration
    from apps.users.models import Role

    # Company - if ANY company exists, use it, don't create id=1
    if Company.objects.exists():
        company = Company.objects.first()
        print(f" - Company: Already exists '{company.name}', skipping.")
    else:
        company, _ = Company.objects.get_or_create(name="Main Company")
        print(f" - Company: Created '{company.name}'.")

    if Branch.objects.exists():
        branch = Branch.objects.first()
        print(f" - Branch: Already exists '{branch.name}', skipping.")
    else:
        branch, _ = Branch.objects.get_or_create(name="Main Branch", company=company)
        print(f" - Branch: Created.")

    if POSTerminal.objects.exists():
        terminal = POSTerminal.objects.first()
        print(f" - Terminal: Already exists, skipping.")
    else:
        terminal, _ = POSTerminal.objects.get_or_create(name="Main Terminal", branch=branch, company=company)
        print(f" - Terminal: Created.")

    if CompanyConfiguration.objects.exists():
        print(f" - CompanyConfiguration: Already exists, skipping.")
    else:
        CompanyConfiguration.objects.get_or_create(company=company, branch=branch)
        print(f" - CompanyConfiguration: Created.")

    if Role.objects.exists():
        print(f" - Roles: Already exists ({Role.objects.count()}), skipping.")
    else:
        for role_name in ['Admin', 'Manager', 'Staff']:
            Role.objects.get_or_create(name=role_name, company=company)
        print(f" - Roles: Created.")

    # ---------------------------------------------------------
    # 2. Accounts - create ONLY if table is empty
    # ---------------------------------------------------------
    if Accounts.objects.exists():
        print(f" - Accounts: Already exists ({Accounts.objects.count()} accounts), skipping creation. No data modified.")
        print("[Accounts Initialization] Complete - no existing data was modified.\n")
        return

    # Table is empty - safe to bulk create
    accounts = [
        Accounts(
            ACC_CODE=acc_code,
            SERIAL_NO=serial_no,
            LEVEL=level,
            TYPE=type_,
            CLASS_FIELD=class_field,
            ACC_NAME=name,
            ENABLE='Y',
        )
        for (acc_code, serial_no, level, type_, class_field, name) in DEFAULT_ACCOUNTS
    ]

    Accounts.objects.bulk_create(accounts, ignore_conflicts=True, batch_size=1000)
    print(f" - Accounts: Created {len(accounts)} default accounts.")
    print("[Accounts Initialization] Complete.\n")











# # accounts/signals.py

# from django.db.models.signals import post_migrate
# from django.dispatch import receiver
# from myaccounts.models import Accounts


# # =========================================================
# # DEFAULT CHART OF ACCOUNTS
# # =========================================================

# DEFAULT_ACCOUNTS = [

#     # =====================================================
#     # MAIN GROUPS (LEVEL 1)
#     # =====================================================

#     {
#         "ACC_CODE": 1,
#         "SERIAL_NO": 1,
#         "LEVEL": 1,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "ASSETS",
#     },

#     {
#         "ACC_CODE": 2,
#         "SERIAL_NO": 26,
#         "LEVEL": 1,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "LIABILITIES",
#     },

#     {
#         "ACC_CODE": 3,
#         "SERIAL_NO": 68,
#         "LEVEL": 1,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "EXPENSES",
#     },

#     {
#         "ACC_CODE": 4,
#         "SERIAL_NO": 91,
#         "LEVEL": 1,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Income",
#         "ACC_NAME": "REVENUE",
#     },

#     # =====================================================
#     # ASSETS SUB GROUPS
#     # =====================================================

#     {
#         "ACC_CODE": 11,
#         "SERIAL_NO": 2,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "CURRENT ASSETS",
#     },

#     {
#         "ACC_CODE": 12,
#         "SERIAL_NO": 24,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "FIXED ASSETS",
#     },

#     {
#         "ACC_CODE": 110,
#         "SERIAL_NO": 3,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "CASH",
#     },

#     {
#         "ACC_CODE": 111,
#         "SERIAL_NO": 5,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "BANK BALANCES",
#     },

#     {
#         "ACC_CODE": 112,
#         "SERIAL_NO": 7,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Asset",
#         "ACC_NAME": "ACCOUNTS RECEIVABLES",
#     },

#     {
#         "ACC_CODE": 117,
#         "SERIAL_NO": 21,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Asset",
#         "ACC_NAME": "RAW MATERIAL/STOCK/INVENTORY",
#     },

#     {
#         "ACC_CODE": 118,
#         "SERIAL_NO": 22,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "FINISHED PRODUCT",
#     },

#     {
#         "ACC_CODE": 121,
#         "SERIAL_NO": 25,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Assets",
#         "ACC_NAME": "FIXED ASSETS",
#     },

#     # =====================================================
#     # LIABILITY SUB GROUPS
#     # =====================================================

#     {
#         "ACC_CODE": 21,
#         "SERIAL_NO": 27,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "EQUITY",
#     },

#     {
#         "ACC_CODE": 22,
#         "SERIAL_NO": 29,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "WITHDRAWALS",
#     },

#     {
#         "ACC_CODE": 23,
#         "SERIAL_NO": 30,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "CURRENT LIABILITIES",
#     },

#     {
#         "ACC_CODE": 211,
#         "SERIAL_NO": 28,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "CAPITAL",
#     },

#     {
#         "ACC_CODE": 231,
#         "SERIAL_NO": 31,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "ACCOUNTS PAYABLE",
#     },

#     {
#         "ACC_CODE": 232,
#         "SERIAL_NO": 64,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "WAGES/LABOUR PAYABLE",
#     },

#     {
#         "ACC_CODE": 233,
#         "SERIAL_NO": 66,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Liability",
#         "ACC_NAME": "FREIGHT PAYABLE",
#     },

#     # =====================================================
#     # EXPENSE GROUPS
#     # =====================================================

#     {
#         "ACC_CODE": 31,
#         "SERIAL_NO": 69,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "COST OF GOODS SOLD",
#     },

#     {
#         "ACC_CODE": 32,
#         "SERIAL_NO": 71,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "PRODUCTION & SELLING EXPENSES",
#     },

#     {
#         "ACC_CODE": 33,
#         "SERIAL_NO": 74,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "ADMINISTRATIVE EXPENSES",
#     },

#     {
#         "ACC_CODE": 34,
#         "SERIAL_NO": 82,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "FINANCIAL EXPENSES",
#     },

#     {
#         "ACC_CODE": 311,
#         "SERIAL_NO": 70,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "COST OF SALES",
#     },

#     {
#         "ACC_CODE": 321,
#         "SERIAL_NO": 72,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "WAGES/LABOUR CHARGES",
#     },

#     {
#         "ACC_CODE": 322,
#         "SERIAL_NO": 73,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Expense",
#         "ACC_NAME": "PACKING EXPENSES",
#     },

#     # =====================================================
#     # REVENUE GROUPS
#     # =====================================================

#     {
#         "ACC_CODE": 41,
#         "SERIAL_NO": 92,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Income",
#         "ACC_NAME": "REVENUE (SALES)",
#     },

#     {
#         "ACC_CODE": 42,
#         "SERIAL_NO": 94,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Income",
#         "ACC_NAME": "TRANSPORTATION INCOME",
#     },

#     {
#         "ACC_CODE": 43,
#         "SERIAL_NO": 95,
#         "LEVEL": 2,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Income",
#         "ACC_NAME": "OTHER INCOME",
#     },

#     {
#         "ACC_CODE": 411,
#         "SERIAL_NO": 93,
#         "LEVEL": 3,
#         "TYPE": "Group",
#         "CLASS_FIELD": "Income",
#         "ACC_NAME": "SALES",
#     },
# ]


# # =========================================================
# # SIGNAL
# # =========================================================

# @receiver(post_migrate)
# def create_default_accounts(sender, **kwargs):

#     """
#     Automatically create default chart of accounts
#     after migration.
#     """
#     if sender.name != 'myaccounts.apps.MyaccountsConfig':
#         return
#     print("Creating Default Accounts...")

#     for acc in DEFAULT_ACCOUNTS:

#         Accounts.objects.get_or_create(

#             ACC_CODE=acc["ACC_CODE"],

#             defaults={

#                 "SERIAL_NO": acc["SERIAL_NO"],

#                 "LEVEL": acc["LEVEL"],

#                 "TYPE": acc["TYPE"],

#                 "CLASS_FIELD": acc["CLASS_FIELD"],

#                 "ACC_NAME": acc["ACC_NAME"],

#                 "ENABLE": "Y",

#             }
#         )


# myaccounts/signals.py