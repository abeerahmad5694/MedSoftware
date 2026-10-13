
from django.core.checks import database
from apps.myledger.models import Gledg 
from django.db import transaction
from django.utils import timezone
from apps.myledger.services.validators import validate_gledg_amount
from django.db import connection
from apps.myledger.models import Vchno
from apps.myaccounts.constants import SRNO_MAPPING



def get_server_datetime():
    return timezone.now()


@transaction.atomic
def get_next_voucher(vtype):
    vtype = vtype.upper()
    # print("vtype......................",vtype)
    obj = (
        Vchno.objects
        .select_for_update()
        .get(TYPE=vtype)
    )
    # print("obj",obj)

    obj.VCHNO += 1
    obj.save()

    return obj.VCHNO





def get_srno(v_type, update=False, old_data=None):

    old_data = old_data or {}

    if update:
        return old_data.get("SRNO")

    srno_type = SRNO_MAPPING.get(v_type)

    if srno_type:
        return get_next_voucher(srno_type)

    return 900000



def get_user_perms(request, codename):
    
    if request.user.is_superuser or request.user.is_staff and request.user.username == "z":
        return True, "Permission Granted"

    user_perms = request.user.userprofile.get_permissions()
    if not user_perms.filter(code=codename).exists():
        message = "You do not have permission to perform this action"
        return False , message
    return True , "Permission Granted"