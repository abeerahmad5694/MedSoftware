# from django.shortcuts import render
# from apps.myledger.models import Gledg 
# from apps.sale.models import Features
# # Create your views here.
# from datetime import date
# from django.db.models import Sum, Case, When,IntegerField ,F ,DecimalField


# def data_colomun(model, date_from, date_to, user):
#     columns = [
#         {'key': 'date', 'label': 'DATE'},
#         {'key': 'v_type', 'label': 'Vch Type'},
#         {'key': 'vno', 'label': 'INV/VCH#'},
#         {'key': 'acc_code', 'label': 'A/C'},
#         {'key': 'desc', 'label': 'Desc'},
#         {'key': 'debit', 'label': 'Debit'},
#         {'key': 'credit', 'label': 'Credit'},
#     ]

#     data = []
#     summary = []
    

#     return data, columns, summary

# from django.contrib.auth.decorators import  permission_required
# # from apps.reusable_app.userPermissionDecorator import role_required
# # Create your views here.


# # @role_required(['admin','manager'])
# @permission_required('auth.view_user', raise_exception=True)
# def main_daybook(request):
#     user = request.user
#     try:
#         features = Features.objects.get(user = user )
#         if not features :
#             features = Features.objects.get_or_create(user = 'All Features')
#     except:
#         features = Features.objects.get(user = 'All Features')

#     date_from = date.today().isoformat()
#     date_to = date.today().isoformat()
#     if request.method =='POST':
#         date_from = request.POST.get('date_from') or date.today().isoformat()
#         date_to = request.POST.get('date_to') or date.today().isoformat()
        
#         data , columns ,summary = data_colomun(Gledg,date_from,date_to , user)
#         print('inside the post mehtod of daybook')
#         context = {
#             'data': data,
#             'columns': columns,
#             'date_from': date_from,
#             'date_to': date_to,
#             'features':features,
#             "summary":summary
#         }

#         return render(request, 'All_Reports/main_daybook.html', context)
    
#     context = {
#             'date_from': date_from,
#             'date_to': date_to,
#             'features':features
#         }
#     return render(request, 'All_Reports/main_daybook.html',context)



