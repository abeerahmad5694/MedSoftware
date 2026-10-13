from django.shortcuts import render
from apps.myledger.models import Gledg 
from apps.sale.models import Features
# Create your views here.
from datetime import date
from django.db.models import Sum, Case, When,IntegerField ,F ,DecimalField
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def data_colomun(model, date_from, date_to, user):
    columns = [
        {'key': 'date', 'label': 'DATE'},
        {'key': 'v_type', 'label': 'Vch Type'},
        {'key': 'vno', 'label': 'INV/VCH#'},
        {'key': 'acc_code', 'label': 'A/C'},
        {'key': 'desc', 'label': 'Desc'},
        {'key': 'debit', 'label': 'Debit'},
        {'key': 'credit', 'label': 'Credit'},
    ]
    data = []
    summary = []

    gledg_rows = model.objects.filter(DATE__range=[date_from, date_to]).order_by('DATE')
    
    # Prepare summary dictionaries
    summary = {
        'Opening Balance': 0.00,
        'Closing Balance': 0.00,
        'Cash Received': 0.00,
        'Cash Paid': 0.00,
        'Cheque/Card Received': 0.00,
        'Cheque/Card Paid': 0.00,
        'Total Sales': 0.00,
        'Total Returns': 0.00,
        'Total Discounts': 0.00,
        'Net Sales': 0.00,
        'Total Collection': 0.00,
        'Qty Sold': 0,
        'Total Item Discount': 0.00,
        'Total Invoice Discount': 0.00,
    }
    # Main loop throughgledg rows
    for row in gledg_rows:
        data.append(
            {
                'date': row.DATE,
                'v_type': row.V_TYPE,
                'vno': row.VNO,
                'acc_code': row.ACC_CODE,
                'desc': row.DESCRIPTION if row.DESCRIPTION else "",
                'debit': 0,
                'credit': 0,
            }
        )
        if row.AMT_TYPE == 'C':
            data[-1]['credit'] = row.AMOUNT
        if row.AMT_TYPE == 'D':
            data[-1]['debit'] = row.AMOUNT

    # Finalize summary calculations
    summary['Net Sales'] = summary['Total Sales'] - summary['Total Returns'] - summary['Total Discounts']
    summary['Total Collection'] = summary['Cash Received'] + summary['Cheque/Card Received']
    summary['Closing Balance'] = summary['Opening Balance'] + summary['Total Collection'] - summary['Cash Paid'] - summary['Cheque/Card Paid']


    
    

    return data, columns, summary

@csrf_exempt
def daybook(request):
    user = request.user
    try:
        features = Features.objects.get(user = user )
        if not features :
            features = Features.objects.get_or_create(user = 'All Features')
    except:
        features = Features.objects.get(user = 'All Features')

    date_from = date.today().isoformat()
    date_to = date.today().isoformat()
    v_type = ""
    if request.method =='POST':
        date_from = request.POST.get('date_from') or date.today().isoformat()
        date_to = request.POST.get('date_to') or date.today().isoformat()
        v_type = request.POST.get('v_type') or ""
        print('v_type',v_type)
        data , columns ,summary = data_colomun(Gledg,date_from,date_to , user)
        context = {
            'data': data,
            'columns': columns,
            'date_from': date_from,
            'date_to': date_to,
            'v_type':v_type,
            'features':features,
            "summary":summary
        }

        return render(request, 'reports/daybook.html', context)
    
    context = {
            'date_from': date_from,
            'date_to': date_to,
            'v_type':v_type,
            'features':features
        }
    return render(request, 'reports/daybook.html',context)



