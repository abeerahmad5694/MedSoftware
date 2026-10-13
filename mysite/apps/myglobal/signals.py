


from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.users.models import Permission, Role, UserProfile
from apps.configuration.models import Company, Branch, POSTerminal, CompanyConfiguration

@receiver(post_migrate)
def create_default_data(sender, **kwargs):
    if sender.name != "apps.myglobal":
        return

    print("\n[System Initialization] Checking existing data...")

    # ---------------------------------------------------------
    # 1. Permissions - create only if not exists, never edit
    # ---------------------------------------------------------
    default_permissions = [
        {'name': 'View Dashboard', 'code': 'view_dashboard', 'module': 'dashboard'},
        
        {'name': 'View Inventory', 'code': 'view_inventory', 'module': 'inventory'},
        {'name': 'Add Item', 'code': 'add_item', 'module': 'inventory'},
        {'name': 'Edit Item', 'code': 'edit_item', 'module': 'inventory'},
        {'name': 'Delete Item', 'code': 'delete_item', 'module': 'inventory'},
        
        
        {'name': 'Create Invoice', 'code': 'create_invoice', 'module': 'sales'},
        {'name': 'Edit Invoice', 'code': 'edit_invoice', 'module': 'sales'},
        {'name': 'View Own Sales', 'code': 'view_own_sales', 'module': 'sales'},
        {'name': 'Return Sale', 'code': 'return_sale', 'module': 'sales'},
        
        
        {'name': 'Create Quotation', 'code': 'create_quotation', 'module': 'quotation'},
        {'name': 'View Own Quotation', 'code': 'view_own_quotation', 'module': 'quotation'},
        
        
        {'name': 'Create Purchase Invoice', 'code': 'create_purchase_invoice', 'module': 'purchase'},
        {'name': 'Edit Purchase', 'code': 'edit_purchase', 'module': 'purchase'},
        {'name': 'View Own Purchases', 'code': 'view_own_purchases', 'module': 'purchase'},
        {'name': 'Return Purchase', 'code': 'return_purchase', 'module': 'purchase'},
        
        
        {'name': 'Create Accounts', 'code': 'create_accounts', 'module': 'accounts'},
        {'name': 'Edit Accounts', 'code': 'edit_accounts', 'module': 'accounts'},
        
        
        {'name': 'View Ledger', 'code': 'view_ledger', 'module': 'ledger'},
        {'name': 'Create Vouchers', 'code': 'create_vouchers', 'module': 'ledger'},
        {'name': 'Edit Vouchers', 'code': 'edit_vouchers', 'module': 'ledger'},
        {'name': 'Delete Vouchers', 'code': 'delete_vouchers', 'module': 'ledger'},
        
        
        {'name': 'Manage Users', 'code': 'manage_users', 'module': 'system'},
        {'name': 'Configure System', 'code': 'configure_system', 'module': 'system'},
        
        
        {'name': 'View Reports (Admin Reports eg. Profit & Loss)', 'code': 'see_reports', 'module': 'reports'},
        {'name': 'View Cost In Reports', 'code': 'see_cost_in_reports', 'module': 'reports'},
        {'name': 'View Payable Statements', 'code': 'see_payable_statements', 'module': 'reports'},
        {'name': 'View Receivables Statements', 'code': 'see_receivables_statements', 'module': 'reports'},
        {'name': 'View Daybook', 'code': 'view_daybook', 'module': 'reports'},
        {'name': 'View Comprehensive Sale', 'code': 'view_comprehensive_sale', 'module': 'reports'},
        {'name': 'View Quotation Book', 'code': 'view_quotation_book', 'module': 'reports'},
        {'name': 'View And Update Inventory in Bulk', 'code': 'view_and_update_inventory_bulk', 'module': 'reports'},
        {'name': 'View And Update Stock Update', 'code': 'stock_update', 'module': 'reports'},
        {'name': 'View Stock Report', 'code': 'view_stock_report', 'module': 'reports'},
    ]

    # if Permission.objects.exists():
    #     print(f" - Permissions: Already exists ({Permission.objects.count()}), skipping creation.")
    # else:
    #     for p_data in default_permissions:
    #         Permission.objects.get_or_create(code=p_data['code'], defaults=p_data)
    #     print(f" - Permissions: Created {len(default_permissions)} permissions.")

        
    created_count = 0
    existing_count = 0

    for p_data in default_permissions:

        permission, created = Permission.objects.get_or_create(
            code=p_data['code'],
            defaults={
                'name': p_data['name'],
                'module': p_data['module'],
            }
        )

        if created:
            created_count += 1
            print(f"   + Permission created: {p_data['code']}")
        else:
            existing_count += 1
            print(f"   - Permission exists: {p_data['code']}")

    print(
        f" - Permissions: {created_count} created, "
        f"{existing_count} already existed."
    )






    # ---------------------------------------------------------
    # 2. Company / Branch / Terminal / Config - create ONLY if empty
    # ---------------------------------------------------------
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
        print(f" - Branch: Created '{branch.name}'.")

    if POSTerminal.objects.exists():
        terminal = POSTerminal.objects.first()
        print(f" - Terminal: Already exists '{terminal.name}', skipping.")
    else:
        terminal, _ = POSTerminal.objects.get_or_create(name="Main Terminal", branch=branch, company=company)
        print(f" - Terminal: Created '{terminal.name}'.")

    if CompanyConfiguration.objects.exists():
        print(f" - CompanyConfiguration: Already exists, skipping.")
        company_config = CompanyConfiguration.objects.first()
    else:
        company_config, _ = CompanyConfiguration.objects.get_or_create(company=company, branch=branch)
        print(f" - CompanyConfiguration: Created.")

    # ---------------------------------------------------------
    # 3. Roles - create only if not exists, assign permissions only on creation
    # ---------------------------------------------------------
    if Role.objects.exists():
        print(f" - Roles: Already exists ({Role.objects.count()}), skipping creation.")
    else:
        default_roles = ['Admin', 'Manager', 'Staff']
        for role_name in default_roles:
            role, created = Role.objects.get_or_create(name=role_name, company=company)
            if created and role_name == 'Admin':
                all_permissions = Permission.objects.all()
                role.permissions.set(all_permissions)
                print(f"   -> Admin Role: {all_permissions.count()} permissions assigned (only on first creation).")
        print(f" - Roles: Created default roles.")

    # ---------------------------------------------------------
    # 4. Superuser - create only if not exists, NEVER update existing
    # ---------------------------------------------------------
    User = get_user_model()
    
    if User.objects.filter(username="z").exists():
        print(f" - Superuser 'z': Already exists, skipping creation.")
        superuser = User.objects.get(username="z")
    else:
        print(f" - Superuser: Creating master account 'z'...")
        superuser = User.objects.create_superuser(
            username="z",
            password="z",
            email="admin@erp.com"
        )
        print(f" - Superuser: Created.")

    # Profile - create only if not exists, never overwrite existing relations
    admin_role = Role.objects.filter(name='Admin').first()
    company = Company.objects.first()
    branch = Branch.objects.first()
    terminal = POSTerminal.objects.first()

    if UserProfile.objects.filter(user=superuser).exists():
        print(f" - Superuser Profile: Already exists, not touching.")
    else:
        UserProfile.objects.create(
            user=superuser,
            role=admin_role,
            company=company,
            branch=branch,
            terminal=terminal
        )
        print(f" - Superuser Profile: Created.")

    print("[System Initialization] Check complete - no existing data was modified.\n")





    
# from django.contrib.auth import get_user_model
# from django.db.models.signals import post_migrate
# from django.dispatch import receiver

# from apps.users.models import Permission, Role, UserProfile
# from apps.configuration.models import Company, Branch, POSTerminal , CompanyConfiguration

# @receiver(post_migrate)
# def create_default_data(sender, **kwargs):
#     """
#     Initializes default system data after migrations.
#     Includes Permissions, Company, Branch, Terminal, Roles, and a Superuser.
#     """
#     # Ensure this runs only for the target app
#     if sender.name != "apps.myglobal":
#         return

#     print("\n[System Initialization] Starting data setup...")

#     # ---------------------------------------------------------
#     # 1. Create Default Permissions
#     # ---------------------------------------------------------
#     default_permissions = [

#         #Dashboard
#         {'name': 'View Dashboard', 'code': 'view_dashboard', 'module': 'dashboard'},
#         # Inventory
#         {'name': 'View Inventory', 'code': 'view_inventory', 'module': 'inventory'},
#         {'name': 'Add Item', 'code': 'add_item', 'module': 'inventory'},
#         {'name': 'Edit Item', 'code': 'edit_item', 'module': 'inventory'},
#         {'name': 'Delete Item', 'code': 'delete_item', 'module': 'inventory'},
#         # Sales
#         {'name': 'Create Invoice', 'code': 'create_invoice', 'module': 'sales'},
#         {'name': 'View Own Sales', 'code': 'view_own_sales', 'module': 'sales'},
#         {'name': 'Return Sale', 'code': 'return_sale', 'module': 'sales'},
        
#         #quotation
#         {'name': 'Create Quotation', 'code': 'create_quotation', 'module': 'quotation'},
#         {'name': 'View Own Quotation', 'code': 'view_own_quotation', 'module': 'quotation'},
        
#         #purchase
#         {'name': 'Create Purchase Invoice', 'code': 'create_purchase_invoice', 'module': 'purchase'},
#         {'name': 'View Own Purchases', 'code': 'view_own_purchases', 'module': 'purchase'},
#         {'name': 'Return Purchase', 'code': 'return_purchase', 'module': 'purchase'},
#         # Accounts
#         {'name': 'Create Accounts', 'code': 'create_accounts', 'module': 'accounts'},
#         {'name': 'Edit Accounts', 'code': 'edit_accounts', 'module': 'accounts'},
#         # myledger
#         {'name': 'View Ledger', 'code': 'view_ledger', 'module': 'ledger'},
#         {'name': 'Create Vouchers', 'code': 'create_vouchers', 'module': 'ledger'},
#         {'name': 'Edit Vouchers', 'code': 'edit_vouchers', 'module': 'ledger'},
#         {'name': 'Delete Vouchers', 'code': 'delete_vouchers', 'module': 'ledger'},
#         # System
#         {'name': 'Manage Users', 'code': 'manage_users', 'module': 'system'},
#         {'name': 'Configure System', 'code': 'configure_system', 'module': 'system'},

#         #reports

#         {'name': 'View Reports (Admin Reports eg. Profit & Loss)', 'code': 'see_reports', 'module': 'reports'},
#         {'name': 'View Cost In Reports', 'code': 'see_cost_in_reports', 'module': 'reports'},
#         {'name': 'View Payable Statements', 'code': 'see_payable_statements', 'module': 'reports'},
#         {'name': 'View Receivables Statements', 'code': 'see_receivables_statements', 'module': 'reports'},

#         {'name': 'View Daybook', 'code': 'view_daybook', 'module': 'reports'},
#         {'name': 'View Comprehensive Sale', 'code': 'view_comprehensive_sale', 'module': 'reports'},
#         {'name': 'View Quotation Book', 'code': 'view_quotation_book', 'module': 'reports'},
#         #{'name': 'View Purchase Invoice Book', 'code': 'view_purchase_invoice_book', 'module': 'reports'},
#         {'name': 'View Stock Report', 'code': 'view_stock_report', 'module': 'reports'},

        


        
        

#     ]

#     for p_data in default_permissions:
#         Permission.objects.get_or_create(code=p_data['code'], defaults=p_data)
    
#     print(" - Permissions: Initialized.")

#     # ---------------------------------------------------------
#     # 2. Create Default Organizational Structure
#     # ---------------------------------------------------------
#     company, _ = Company.objects.get_or_create(name="Main Company")
#     branch, _ = Branch.objects.get_or_create(name="Main Branch", company=company)
#     terminal, _ = POSTerminal.objects.get_or_create(name="Main Terminal", branch=branch, company=company)
#     company_config, _ = CompanyConfiguration.objects.get_or_create(company=company, branch=branch)

#     # ---------------------------------------------------------
#     # 3. Create Default Custom Roles
#     # ---------------------------------------------------------
#     # default_roles = ['Admin', 'Manager', 'Staff']
#     # for role_name in default_roles:
#     #     Role.objects.get_or_create(name=role_name, company=company)

#     # ---------------------------------------------------------
# # 3. Create Default Custom Roles
# # ---------------------------------------------------------
#     default_roles = ['Admin', 'Manager', 'Staff']

#     for role_name in default_roles:
#         role, _ = Role.objects.get_or_create(
#             name=role_name,
#             company=company
#         )

#         # Give Admin role ALL permissions
#         if role_name == 'Admin':
#             all_permissions = Permission.objects.all()
#             role.permissions.set(all_permissions)

#             print(f" - Admin Role: {all_permissions.count()} permissions assigned.")


#     # ---------------------------------------------------------
#     # 4. Create Superuser and assigned Profile
#     # ---------------------------------------------------------
#     User = get_user_model()
    
#     superuser = User.objects.filter(username="z").first()
#     if not superuser:
#         print(" - Superuser: Creating master account 'VM'...")
#         superuser = User.objects.create_superuser(
#             username="z",
#             password="z",
#             email="admin@erp.com"
#         )
#     else:
#         print(" - Superuser: Master account VM already exists.")
        
#     # Initialize Profile for Superuser
#     admin_role = Role.objects.filter(name='Admin', company=company).first()
#     profile, created = UserProfile.objects.get_or_create(
#         user=superuser,
#         defaults={
#             'role': admin_role,
#             'company': company,
#             'branch': branch,
#             'terminal': terminal
#         }
#     )
#     if created:
#         print(" - Superuser Profile: Created and configured.")
#     else:
#         # Ensure relationships are populated to avoid crashes
#         if not profile.company or not profile.branch or not profile.terminal or not profile.role:
#             profile.role = profile.role or admin_role
#             profile.company = profile.company or company
#             profile.branch = profile.branch or branch
#             profile.terminal = profile.terminal or terminal
#             profile.save()
#             print(" - Superuser Profile: Default relationships updated.")

#     print("[System Initialization] Data setup complete.\n")