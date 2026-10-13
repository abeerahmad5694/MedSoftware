from django.db import connection
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_retvchno_func_in_sql(sender, **kwargs):
    
    if sender.name != 'myledger':
        return
    print('creating retvchno function......')
    with connection.cursor() as cursor:
        cursor.execute("""
        DROP FUNCTION IF EXISTS `retvchno`;
        CREATE FUNCTION `retvchno`(vtypes CHAR(3)) RETURNS int(11)
                BEGIN
                if exists (select jan from vchno where `type` = vtypes AND jan=1) then
                RETURN 0;
                else
                UPDATE vchno
                SET vchno = vchno + 1,jan=1
                WHERE `type` = vtypes;
                UPDATE vchno
                SET jan=0
                WHERE `type` = vtypes;
                RETURN (SELECT vchno FROM vchno WHERE `type` = vtypes);
                end if;
                END
        """)
