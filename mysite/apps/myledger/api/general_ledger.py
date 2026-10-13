from django.http import JsonResponse
from django.db.models import Sum
from datetime import date, datetime
from decimal import Decimal
from apps.myledger.models import Gledg
from apps.sale.models import Invoice, Features
from apps.purchase.models import Purchase
from apps.myledger.services.helpers import get_user_perms
from apps.myaccounts.models import Accounts

def create_ledger_rows(acc_code, from_date, to_date):
    """
    Optimized ledger engine matching daybook's code structure.
    Fetches Invoice, Purchase, and Gledg records, sorts by dateent with
    source priority, and tracks running balance.
    """
    # 1. Columns declaration
    columns = [
        {"key": "v_type", "label": "VTYPE", "width": "46px"},
        {"key": "date", "label": "DATE", "width": "82px"},
        {"key": "vno", "label": "VCH #", "width": "64px"},
        {"key": "desc", "label": "DESCRIPTION", "width": "auto"},
        {"key": "amount", "label": "AMOUNT", "width": "100px"},
        {"key": "debit", "label": "DEBIT +", "width": "100px"},
        {"key": "credit", "label": "CREDIT -", "width": "100px"},
        {"key": "balance", "label": "BALANCE", "width": "110px"},
    ]

    # 2. Historical balance calculation
    prev_debit_gledg = Gledg.objects.filter(
        ACC_CODE=acc_code, 
        DATE__lt=from_date, 
        AMT_TYPE='DR'
    ).aggregate(total=Sum('AMOUNT'))['total'] or Decimal('0.00')

    prev_credit_gledg = Gledg.objects.filter(
        ACC_CODE=acc_code, 
        DATE__lt=from_date, 
        AMT_TYPE='CR'
    ).aggregate(total=Sum('AMOUNT'))['total'] or Decimal('0.00')

    prev_debit_inv = Invoice.objects.filter(
        header_acc_code=acc_code, 
        date__lt=from_date, 
        is_header=True
    ).aggregate(total=Sum('header_net_total'))['total'] or Decimal('0.00')

    prev_credit_pur = Purchase.objects.filter(
        header_acc_code=acc_code, 
        date__lt=from_date, 
        is_header=True
    ).aggregate(total=Sum('header_net_total'))['total'] or Decimal('0.00')

    running_balance = Decimal(str((prev_debit_gledg + prev_debit_inv) - (prev_credit_gledg + prev_credit_pur)))

    account = Accounts.objects.filter(ACC_CODE=acc_code).first()
    if account:
        op_bal = Decimal(str(account.OPENING_BALANCE or 0.0))
        bal_type = (account.BALANCE_TYPE or '').strip().upper()
        if bal_type == 'DR':
            running_balance += op_bal
        else:
            running_balance -= op_bal

    # Opening row
    bal_sign = 'Dr' if running_balance >= 0 else 'Cr'
    data = [{
        'DATE':        str(from_date),
        'V_TYPE':      '',
        'VNO':         '',
        'DESCRIPTION': 'Opening Balance',
        'REMARKS':     '',
        'AMOUNT':      '',
        'AMT_TYPE':    '',
        'DEBIT':       '',
        'CREDIT':      '',
        'BALANCE':     f"{abs(running_balance):,.2f} {bal_sign}",
        'CHQNO':       '',
        'RECEIPTNO':   '',
    }]

    # 3. Data query and merging
    inv_rows = Invoice.objects.filter(
        header_acc_code=acc_code, 
        date__range=(from_date, to_date), 
        is_header=True
    ).values('id', 'bill_no', 'date', 'dateent', 'header_net_total', 'header_remarks')

    pur_rows = Purchase.objects.filter(
        header_acc_code=acc_code, 
        date__range=(from_date, to_date), 
        is_header=True
    ).values('id', 'bill_no', 'date', 'dateent', 'header_net_total', 'header_remarks')

    gledg_rows = Gledg.objects.filter(
        ACC_CODE=acc_code, 
        DATE__range=(from_date, to_date)
    ).values('GLEDG_ID', 'V_TYPE', 'VNO', 'DATE', 'DESCRIPTION', 'AMOUNT', 'AMT_TYPE', 'DATEENT')

    all_rows = []

    for r in inv_rows:
        all_rows.append({
            'date': r['date'],
            'dateent': r['dateent'],
            'v_type': 'INV',
            'vno': r['bill_no'],
            'desc': r['header_remarks'] or 'Sales Invoice',
            'debit': r['header_net_total'] or Decimal('0.00') if r['header_net_total'] > 0 else Decimal('0.00') ,
            'credit': abs(r['header_net_total']) or Decimal('0.00') if r['header_net_total'] < 0 else Decimal('0.00'),
            'source': 'invoice',
            'id': r['id']
        })

    for r in pur_rows:
        all_rows.append({
            'date': r['date'],
            'dateent': r['dateent'],
            'v_type': 'PUR',
            'vno': r['bill_no'],
            'desc': r['header_remarks'] or 'Purchase',
            'debit': abs(r['header_net_total']) or Decimal('0.00') if r['header_net_total'] < 0 else Decimal('0.00') ,
            'credit': abs(r['header_net_total']) or Decimal('0.00') if r['header_net_total'] > 0 else Decimal('0.00'),
            # 'debit': Decimal('0.00'),
            # 'credit': r['header_net_total'] or Decimal('0.00'),
            'source': 'purchase',
            'id': r['id']
        })

    for r in gledg_rows:
        amount = r['AMOUNT'] or Decimal('0.00')
        debit = amount if r['AMT_TYPE'] == 'DR' else Decimal('0.00')
        credit = amount if r['AMT_TYPE'] == 'CR' else Decimal('0.00')
        all_rows.append({
            'date': r['DATE'],
            'dateent': r['DATEENT'],
            'v_type': r['V_TYPE'],
            'vno': r['VNO'],
            'desc': r['DESCRIPTION'],
            'debit': debit,
            'credit': credit,
            'source': 'gledg',
            'id': r['GLEDG_ID']
        })

    # Sort key prioritization: invoice (1), purchase (2), then gledg (3)
    source_priority = {
        'invoice': 1,
        'purchase': 2,
        'gledg': 3,
    }

    def get_sort_key(row):
        d_ent = row['dateent']
        if d_ent is None:
            sort_dateent = datetime.min
        elif isinstance(d_ent, datetime):
            sort_dateent = d_ent
        elif isinstance(d_ent, date):
            sort_dateent = datetime.combine(d_ent, datetime.min.time())
        else:
            sort_dateent = d_ent
        
        priority = source_priority.get(row['source'], 99)
        return (sort_dateent, priority, str(row['vno'] or ''), row['id'] or 0)

    all_rows.sort(key=get_sort_key)

    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')

    # Process and append sorted rows
    for row in all_rows:
        debit = row['debit']
        credit = row['credit']
        running_balance += debit - credit

        total_debit += debit
        total_credit += credit

        bal_sign = 'Dr' if running_balance >= 0 else 'Cr'
        amount = debit if debit > 0 else credit

        data.append({
            'DATE':        str(row['date']),
            'V_TYPE':      row['v_type'] or '',
            'VNO':         row['vno'] or '',
            'DESCRIPTION': (row['desc'] or '').strip(),
            'REMARKS':     '',
            'AMOUNT':      str(amount) if amount else '',
            'AMT_TYPE':    'DR' if debit > 0 else 'CR' if credit > 0 else '',
            'DEBIT':       str(debit) if debit else '',
            'CREDIT':      str(credit) if credit else '',
            'BALANCE':     f"{abs(running_balance):,.2f} {bal_sign}",
            'CHQNO':       '',
            'RECEIPTNO':   '',
        })

    # 4. Summary calculation
    closing_sign = 'Dr' if running_balance >= 0 else 'Cr'
    summary = {
        'total_debit':     str(total_debit),
        'total_credit':    str(total_credit),
        'closing_balance': f"{abs(running_balance):,.2f} {closing_sign}",
        'count':           len(data),
    }

    return data, columns, summary



def general_ledger(request, acc_code, from_date, to_date):
    """
    Returns general ledger JSON response for a given account in date range.
    Uses ultra-optimized create_ledger_rows to fetch and build transaction rows.
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'GET required'}, status=405)

    if not acc_code:
        return JsonResponse({'success': False, 'message': 'Account code required'}, status=200)

    has_permission, message = get_user_perms(request, "view_ledger")
    if not has_permission:
        return JsonResponse({'success': False, 'message': message}, status=200)

    try:
        acc_code = int(acc_code)
        parsed_from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        parsed_to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'message': f'Invalid request arguments: {str(e)}'}, status=200)

    data, columns, summary = create_ledger_rows(acc_code, parsed_from_date, parsed_to_date)
    return JsonResponse({
        'success': True,
        'message': 'General Ledger fetched successfully.',
        'data': data,
        'columns': columns,
        **summary
    })