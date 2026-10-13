
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pytz # type:ignore  

# karachi_tz = pytz.timezone('Asia/Karachi')

# def karachi_now():
#     return timezone.now().astimezone(karachi_tz)




from simple_history.models import HistoricalRecords


class Quotation(models.Model):
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
    dateent = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    dateedit = models.DateTimeField(null=True, blank=True)
    user = models.CharField(max_length=150, blank=True, default='',null = True)
    edit_by = models.CharField(max_length=150, blank=True, default='',null = True)
    salesman = models.CharField(max_length=150, blank=True, default='',null = True)
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, null=True, blank=True)
    posterminal = models.ForeignKey('configuration.POSTerminal', on_delete=models.CASCADE, null=True, blank=True)

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
        db_table = 'quotation'
        indexes = [
            models.Index(fields=['bill_no']),
            models.Index(fields=['is_header']),
            models.Index(fields=['date', 'is_header']),
            models.Index(fields=['posterminal', 'date']),
            models.Index(fields=['is_header', 'header_net_total']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(header_payment_mode__in=[1, 2, 3]),
                name='quotation_valid_payment_mode'
            ),
            models.CheckConstraint(
                condition=models.Q(is_header=True, header_total_items__gte=0) |
                    models.Q(is_header=False, header_total_items=0),
                name='quotation_total_items_only_on_header'
            ),
        ]
        # unique_together = ['bill_no', 'row_no']
