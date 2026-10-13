import datetime
from django.utils import timezone
import pytz
from django.forms.models import model_to_dict
from django.db import transaction
from apps.myledger.models import Vchno
class DateTimeHelper:
    def get_server_time(self):
        # With USE_TZ = False, this returns local Asia/Karachi time
        return timezone.now()
    
    def get_local_time(self):
        # Simply returns timezone.now() as it is already local
        return timezone.now()


def get_user_perms(request, codename):
    if not hasattr(request, '_user_perm_codes'):
        request._user_perm_codes = set(request.user.userprofile.get_permissions().values_list('code', flat=True))
        
    if codename not in request._user_perm_codes:
        message = "You do not have permission to perform this action"
        return False, message
    return True, "Permission Granted"




@transaction.atomic
def get_next_voucher(vtype):
    vtype = vtype.upper()
    obj, created = Vchno.objects.select_for_update().get_or_create(TYPE=vtype, defaults={'VCHNO': 0})

    obj.VCHNO += 1
    obj.save()

    return obj.VCHNO
