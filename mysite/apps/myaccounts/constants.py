DETAIL_LEVEL = 4
DETAIL = 'Detail'
GROUP = 'Group'




SRNO_MAPPING = {

    "JV": "GSRNO",
    "CR": "GSRNO",
    "CP": "GSRNO",
    "BR": "GSRNO",  
    "BP": "GSRNO",

    "INV": "ISRNO",

    "PUR": "PSRNO",
}



DEFAULT_ACCOUNTS = {
    "CASH_IN_HAND_ACCOUNT": "110000001",
    "BANK_ACCOUNT": "111000001",
    "SALES_DISCOUNT_ACCOUNT": "330000001",
    "PURCHASE_DISCOUNT_ACCOUNT": "430000001",
}


def get_default_account(key, company_id=None, branch_id=None):
    """
    Returns dynamic default account code by key.
    Checks configuration DefaultAccounts selector first, then falls back to DEFAULT_ACCOUNTS.
    """
    from apps.configuration.selectors import get_default_account_code
    key_mapping = {
        'CASH_IN_HAND_ACCOUNT': 'default_cash_acc',
        'BANK_ACCOUNT': 'default_bank_acc',
        'SALES_DISCOUNT_ACCOUNT': 'sales_discount_acc',
        'PURCHASE_DISCOUNT_ACCOUNT': 'purchase_discount_acc',
    }
    config_key = key_mapping.get(key, key)
    fallback = int(DEFAULT_ACCOUNTS.get(key, 112000001))
    return str(get_default_account_code(config_key, company_id=company_id, branch_id=branch_id) or fallback)