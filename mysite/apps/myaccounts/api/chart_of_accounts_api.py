from django.http import JsonResponse
from apps.myaccounts.models import Accounts
from django.core.paginator import Paginator
from django.db.models import Q

from apps.myaccounts.constants import *

def get_group_tree(request):
    try:
        # Fetch all group accounts (Levels 1, 2, 3)
        groups = Accounts.objects.filter(TYPE__iexact=GROUP,LEVEL__lt=DETAIL_LEVEL).values(
            'ACC_CODE', 'ACC_NAME', 'LEVEL', 'TYPE', 'CLASS_FIELD'
        ).order_by('ACC_CODE')
        data = [
            {
                'id': str(g['ACC_CODE']),
                'code': str(g['ACC_CODE']),
                'name': g['ACC_NAME'] or '',
                'level': g['LEVEL'],
                'type': g['TYPE'] or '',
                'class_field': g['CLASS_FIELD'] or 'group',
            }
            for g in groups
        ]
        # print('data',data)
            
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        print('error', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_detail_accounts(request):
    try:
        parent_code = request.GET.get('parent_code', '')
        search = request.GET.get('search', '')
        page_num = int(request.GET.get('page', 1))
        
        if not parent_code:
            return JsonResponse({'success': False, 'error': 'Parent code required'}, status=400)
        
        # print(parent_code)
        # Detail accounts for this parent start with the parent code
        qs = Accounts.objects.filter(TYPE=DETAIL,LEVEL=DETAIL_LEVEL,ACC_CODE__startswith=str(parent_code)).only('ACC_CODE','CITY','ACC_NAME','TYPE','MOBILE_NO').order_by('ACC_CODE')
        # print('qs = ',qs)        
        if search:
            qs = qs.filter(Q(ACC_NAME__icontains=search) | Q(ACC_CODE__icontains=search))
            
        paginator = Paginator(qs, 20) # 50 per page
        page = paginator.get_page(page_num)
        
        data = []
        for d in page.object_list:
            data.append({
                'code': str(d.ACC_CODE),
                'name': d.ACC_NAME or '',
                # 'balance': d.OPENING_BALANCE or 0.0,
                # 'type': d.TYPE or '',
                # 'city': d.CITY or '',
                # 'mobile': d.MOBILE_NO or ''
            })
            
        return JsonResponse({
            'success': True,
            'data': data,
            'pagination': {
                'total': paginator.count,
                'pages': paginator.num_pages,
                'current_page': page.number,
                'has_next': page.has_next(),
                'has_prev': page.has_previous()
            }
        })
    except Exception as e:
        print('exepction',e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
