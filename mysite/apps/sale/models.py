
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pytz # type:ignore  

# karachi_tz = pytz.timezone('Asia/Karachi')

# def karachi_now():
#     return timezone.now().astimezone(karachi_tz)




# class Vchno(models.Model):
#     type = models.CharField(max_length=3, blank=True, null=True)
#     vchno = models.IntegerField(blank=True, null=True)
#     remarks = models.CharField(max_length=50, blank=True, null=True)
#     jan = models.IntegerField(blank=True, null=True)
#     feb = models.IntegerField(blank=True, null=True)
#     mar = models.IntegerField(blank=True, null=True)
#     apr = models.IntegerField(blank=True, null=True)
#     may = models.IntegerField(blank=True, null=True)
#     jun = models.IntegerField(blank=True, null=True)
#     jul = models.IntegerField(blank=True, null=True)
#     aug = models.IntegerField(blank=True, null=True)
#     sep = models.IntegerField(blank=True, null=True)
#     oct = models.IntegerField(blank=True, null=True)
#     nov = models.IntegerField(blank=True, null=True)
#     dece = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = False
#         db_table = 'vchno'


        

from simple_history.models import HistoricalRecords


class Invoice(models.Model):
    # === PK ===
    id = models.BigAutoField(primary_key=True)

    # === Bill grouping (essential — NOT nullable) ===
    bill_no = models.IntegerField(db_index=True)
    # row_no = models.PositiveSmallIntegerField()
    is_header = models.BooleanField(default=False, db_index=True)

    # === Row-level fields ===
    header_edit_count = models.PositiveIntegerField(default=0, null=True, blank=True)
    header_acc_code = models.IntegerField(default = 112000001, null=True, blank=True)
    inv_id = models.IntegerField(null=True, blank=True)
    prod_name = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='',null = True)
    qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    uom = models.CharField(max_length=20, blank=True, default='',null = True)
    packing_mode = models.PositiveSmallIntegerField(default=1, null=True, blank=True,
        db_comment='1=base 2=ctrn 3=dzn 4=wholesale')
    
    pack_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True,
        db_comment='crtn_qty if packing mode=2, dzn_qty if packing mode=3')
    row_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    row_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    row_net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    row_net_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    row_rate_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    
    row_notes = models.TextField(blank=True, default='',null = True)

    # === Header-only fields ===
    date = models.DateField(null=True, blank=True, db_index=True)
    dateent = models.DateTimeField(null=True, blank=True)
    dateedit = models.DateTimeField(null=True, blank=True)
    user = models.CharField(max_length=150, blank=True, default='',null = True)
    edit_by = models.CharField(max_length=150, blank=True, default='',null = True)
    salesman = models.CharField(max_length=150, blank=True, default='',null = True)
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, null=True, blank=True)
    posterminal = models.ForeignKey('configuration.POSTerminal', on_delete=models.CASCADE, null=True, blank=True)


    # quotation converted logic header
    header_quo_con_by = models.CharField(max_length=150, blank=True, default='',null = True)
    header_quo_con_no = models.IntegerField(null=True, blank=True)

    # === Header totals ===
    header_total_items = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    header_item_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    header_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_delivery_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    header_gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_msc_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, db_index=True)
    header_remarks = models.TextField(blank=True, default='',null = True)

    # === Payment fields ===
    header_payment_mode = models.PositiveSmallIntegerField(default=1, null=True, blank=True,
        db_comment='1=cash 2=bank 3=dual')
    header_cash_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_bank_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_card_last4 = models.CharField(max_length=4, blank=True, default='',null = True)
    header_total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        managed = True
        db_table = 'invoice'
        indexes = [
            models.Index(fields=['bill_no']),
            models.Index(fields=['header_quo_con_no']),
            models.Index(fields=['is_header']),
            models.Index(fields=['date', 'is_header']),
            models.Index(fields=['posterminal', 'date']),
            models.Index(fields=['is_header', 'header_net_total']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(header_payment_mode__in=[1, 2, 3]),
                name='valid_payment_mode'
            ),
            models.CheckConstraint(
                condition=models.Q(is_header=True, header_total_items__gte=0) |
                    models.Q(is_header=False, header_total_items=0),
                name='total_items_only_on_header'
            ),
        ]
        # unique_together = ['bill_no', 'row_no']



# class Gledg(models.Model):
#     gledg_id = models.AutoField(primary_key=True)
#     acc_code = models.IntegerField(blank=True, null=True)
#     ref_acc_code = models.IntegerField()
#     v_type = models.CharField(max_length=2, blank=True, null=True)
#     vno = models.IntegerField(blank=True, null=True)
#     date = models.DateField(blank=True, null=True)
#     desc = models.CharField(max_length=250, db_collation='latin1_general_ci', blank=True, null=True)
#     remarks = models.CharField(max_length=60, blank=True, null=True)
#     amount = models.FloatField(blank=True, null=True)
#     amt_type = models.CharField(max_length=2, blank=True, null=True)
#     chqno = models.CharField(max_length=15, blank=True, null=True)
#     ref_no = models.IntegerField(blank=True, null=True, db_comment='computer_do_no')
#     dateent = models.DateTimeField(blank=True, null=True)
#     dateedit = models.DateTimeField(blank=True, null=True)
#     user = models.CharField(max_length=10, db_collation='latin1_general_ci', blank=True, null=True)
#     editby = models.CharField(max_length=10, blank=True, null=True)
#     branchid = models.IntegerField(blank=True, null=True)
#     receiptno = models.IntegerField(blank=True, null=True)
#     shift = models.CharField(max_length=1, blank=True, null=True)
#     cheque_date = models.DateField()
#     drawn_branch = models.CharField(max_length=35)
#     paymentmethod = models.CharField(max_length=12)
#     upload = models.CharField(max_length=1)
#     show_in_sale_rpt = models.CharField(max_length=1, blank=True, null=True)
#     isposted = models.CharField(max_length=1)
#     inv_yes_no = models.CharField(max_length=1)
#     bank_reconcile = models.CharField(max_length=1)
#     actual_installment = models.IntegerField()
#     pur_inv = models.CharField(db_column='Pur_Inv', max_length=1)  # Field name made lowercase.
#     station = models.CharField(max_length=5, db_collation='latin1_general_ci')
#     prod_categ = models.CharField(max_length=25, db_collation='latin1_general_ci')

#     class Meta:
#         managed = False
#         db_table = 'gledg'






class BarcodConfig(models.Model):
    user = models.CharField(max_length=10, blank=True, null=True)
    price_base = models.CharField(max_length=1,choices=[('N','Normal'),('P','Pice Embeded')])
    total_bc_digits = models.PositiveSmallIntegerField(default=13)
    left_delete = models.PositiveSmallIntegerField(default = 2)
    right_delete =models.PositiveSmallIntegerField(default = 1)
    item_bc = models.PositiveSmallIntegerField(default=5)
    kg= models.PositiveSmallIntegerField(default=2)
    grm= models.PositiveSmallIntegerField(default=3)


    class Meta:
        managed = True
        db_table = 'ab_BarcodConfig'

    def __str__(self):
        return f'This is barcode configration of {self.user}'
    



class Features(models.Model):
    user = models.CharField(max_length=50,default="All Features")
    pos_discount_per_item = models.BooleanField(default=True)
    pos_load_prv_bill = models.BooleanField(default=True)
    pos_disc_flat_limit = models.FloatField(null=True,blank=True)


    