from apps.configuration.models import CompanyConfiguration, DefaultAccounts, Company, Branch

DEFAULT_CONFIG_DATA = {
    'pos': {
        'max_row_discount_percent': 0,
        'max_row_discount_amount': 0,
        'max_total_discount_percent': 0,
        'row_discount_allowed': True,
        'delivery_charges_allowed': True,
        'tax_charges_allowed': True,
        'msc_charges_allowed': True,
        'total_gst_percent': 0,
        'default_page_size': 'thermal_80',
        'default_direct_print_checked': True,
        'allow_to_decrease_price': True,
        'allow_negative_sale': True,
        'require_remarks': False,
        'foc_allowed': False,
    },
    'purchase': {
        'max_row_discount_percent': 0,
        'max_row_discount_amount': 0,
        'max_total_discount_percent': 0,
        'freight_charges_allowed': True,
        'labour_charges_allowed': True,
        'unload_charges_allowed': True,
        'default_page_size': 'thermal_80',
        'default_direct_print_checked': False,
        'auto_update_cost_price': True,
        'foc_allowed': False,
    },
    'quotation': {
        'default_page_size': 'thermal_80',
        'default_direct_print_checked': False,
        'quotation_validity_days': 30,
        'auto_convert_to_bill': True,
    },
    'vouchers': {
        'default_page_size': 'thermal_80',
        # 'default_direct_print_checked': False,
    },
    'inventory': {
        'allow_negative_stock': False,
        'enable_expiry_tracking': True,
        'enable_low_stock_alerts': True,
        'pictures_allowed': False,
    },
    'dashboard': {
        'default_period': 'today',
    },
    'general': {
        'multiple_bill_prints': 1,
        'currency_symbol': 'Rs',
        'company_tagline': '',
        'online_software': True,
    },
}

DEFAULT_ACCOUNTS_DATA = {
    'cash_client_acc': 112000001,
    # 'sales_counter_acc': 110000001,
    'sales_revenue_acc': 411000001,

    'sales_discount_acc': 330000001,
    # 'delivery_income_acc': 412000001,
    'sales_tax_payable_acc': 234000001,

    # 'default_supplier_acc': 231000001,
    # 'purchase_expense_acc': 311000001,
    'purchase_discount_acc': 430000001,
    'freight_payable_acc': 231000124,
    'labour_payable_acc': 231000123,
    'unload_payable_acc': 231000125,

    'default_cash_acc': 110000001,
    'default_bank_acc': 111000001,
    'default_opening_stock': 231000001,

    # 'petty_cash_acc': 110000002,
    'ar_control_parent': 112,
    'ap_control_parent': 231,
}


def get_company_config(company_id=None, branch_id=None):
    """
    Retrieve company configuration with merged defaults without falling back
    to another company's saved configuration.
    """
    config_obj = None
    if company_id and branch_id:
        config_obj = CompanyConfiguration.objects.filter(company_id=company_id, branch_id=branch_id).first()
    if not config_obj and company_id:
        config_obj = CompanyConfiguration.objects.filter(company_id=company_id).first()
    elif not config_obj and branch_id:
        config_obj = CompanyConfiguration.objects.filter(branch_id=branch_id).first()

    # Keep the legacy global fallback only for callers with no tenant context.
    if not config_obj and company_id is None and branch_id is None:
        config_obj = CompanyConfiguration.objects.first()

    merged = {}
    for module, defaults in DEFAULT_CONFIG_DATA.items():
        merged[module] = defaults.copy()
        if config_obj and config_obj.config_data and module in config_obj.config_data:
            merged[module].update(config_obj.config_data[module])

    return merged, config_obj


def get_default_accounts(company_id=None, branch_id=None):
    """
    Retrieve default account mappings with merged defaults, scoped by tenant.
    """
    acc_obj = None
    if company_id and branch_id:
        acc_obj = DefaultAccounts.objects.filter(company_id=company_id, branch_id=branch_id).first()
    if not acc_obj and company_id:
        acc_obj = DefaultAccounts.objects.filter(company_id=company_id).first()
    elif not acc_obj and branch_id:
        acc_obj = DefaultAccounts.objects.filter(branch_id=branch_id).first()

    # Do not borrow another company's account mapping when a tenant was supplied.
    if not acc_obj and company_id is None and branch_id is None:
        acc_obj = DefaultAccounts.objects.first()

    merged = DEFAULT_ACCOUNTS_DATA.copy()
    if acc_obj and acc_obj.accounts_data:
        merged.update(acc_obj.accounts_data)

    return merged, acc_obj


def get_default_account_code(key, company_id=None, branch_id=None):
    """
    Return a specific default account code by key, with its configured fallback.
    """
    accounts, _ = get_default_accounts(company_id=company_id, branch_id=branch_id)
    return accounts.get(key, DEFAULT_ACCOUNTS_DATA.get(key, 112000001))
