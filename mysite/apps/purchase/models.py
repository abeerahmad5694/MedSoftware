from django.db import models

# Create your models here.






class Purchase(models.Model):
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
    foc_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True)
    
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    uom = models.CharField(max_length=20, blank=True, default='',null = True)
    packing_mode = models.PositiveSmallIntegerField(default=1, null=True, blank=True,
        db_comment='1=base 2=ctrn 3=dzn 4=wholesale')
    
    pack_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True,
        db_comment='crtn_qty if packing mode=2, dzn_qty if packing mode=3')
    row_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    row_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    row_net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
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
    header_payment_mode = models.IntegerField(default=112000001, null=True, blank=True,
        db_comment='112000001=cash , any other = card')
    header_cash_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_bank_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_card_last4 = models.CharField(max_length=4, blank=True, default='',null = True)
    header_total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    #======== Purchae Specific===========

    header_labour_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_freight_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_unload_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    header_freight_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    header_labour_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    header_unload_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    
    # === Supplier Bill Reference - HEADER ONLY ===
    header_supl_inv_no = models.CharField(max_length=35, blank=True, default='', null=True, 
        help_text="Supplier invoice number")
    header_supl_inv_date = models.DateField(null=True, blank=True, 
        help_text="Supplier invoice date")

                        # Internal Ref - HEADER LEVEL ===
    header_our_ref = models.CharField(max_length=25, blank=True, default='', null=True,
        help_text="Our PO reference, When did we order this inovice")
    header_our_ref_date = models.DateField(null=True, blank=True)
    
    # === Foreign Currency - HEADER ONLY for most cases ===
    fc_currency = models.CharField(max_length=3, default='PKR', blank=True, null=True,
        help_text="USD, AED, CNY. PKR if local purchase")
    fc_rate = models.DecimalField(max_digits=11, decimal_places=4, default=0, null=True, blank=True,
        help_text="Exchange rate on bill date. 0 if PKR")
    fc_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True,
        help_text="Total invoice value in foreign currency")

    # If item-wise FC needed - ROW LEVEL
    row_fc_rate = models.DecimalField(max_digits=11, decimal_places=4, default=0, null=True, blank=True)
    row_fc_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)



    # === Landed Cost - ROW LEVEL ===
    row_total_cost_per_base_unit = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, blank=True,
        help_text="Landed cost per unit after freight/unload/shortage")
    row_batch_no = models.CharField(max_length=15, blank=True, default='', null=True)
    row_batch_qty = models.PositiveIntegerField(default=0, null=True, blank=True)
    row_expiry_dt = models.DateField(null=True, blank=True)
    row_pack_qty_rcvd = models.PositiveIntegerField(default=0, null=True, blank=True,
        help_text="Actually received vs pack_qty ordered")
    
    row_remaining_qty = models.PositiveIntegerField(default=0, null=True, blank=True,
        help_text="Remaining base_qty after sale")



    # === Tax - HEADER LEVEL ===
    header_wht_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True, help_text='Example: You buy goods Rs. 100,000 from an unregistered supplier. FBR rate = 4.5% WHT.header_wht_percent = 4.5header_wht_amount = 4500You pay supplier 95,500. You deposit 4,500 to FBR via CPR.')
    header_wht_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_advtax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)

    header_advtax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_gst_after_discount = models.BooleanField(default=True, 
        help_text="If False, calc GST before discount")



    # === Freight/Builty - HEADER LEVEL ===
    header_builty_no = models.CharField(max_length=15, blank=True, default='', null=True,help_text='Related to transporter')
    header_builty_date = models.DateField(null=True, blank=True)
    header_delivery_person = models.CharField(max_length=150, blank=True, default='', null=True)
    header_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_shortaccess = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True,
        help_text="Shortage/Access amount")

    # === Store + Status - HEADER LEVEL ===
    # store = models.ForeignKey('configuration.Store', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, default='posted', choices=[('pending','Pending'),('received','Received'),('posted','Posted')])


        # === Pricing - ROW LEVEL ===
    row_trade_price = models.DecimalField(max_digits=12, decimal_places=4, default=0, null=True, blank=True,
        help_text="Trade Price,What you sell")
    row_actual_retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True,
        help_text="Retail Price") 
    row_oldcost = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, blank=True,
        help_text="Previous cost for profit calc")

    # === Extra Discounts - ROW LEVEL ===
    row_discount_percent2 = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    row_discount_amount2 = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    # row_bonus = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True,
    #     help_text="Free bonus qty")
    row_bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    
    po_created_by = models.CharField(max_length=15, blank=True, default='', null=True,help_text='Who created the PO')
    po_bill_no =models.IntegerField(db_index=True, null= True, blank=True,help_text='Related to PO')
    
    
    header_pur_type = models.CharField(max_length=50, default='p', null=True, blank=True, help_text="purchase=p, purchase_return=pr, purchase_order=po, consignment_in=cin")
    
    class Meta:
        managed = True
        db_table = 'purchase'
        indexes = [
            models.Index(fields=['bill_no'], name='purchase_bill_no_idx'),
            models.Index(fields=['is_header'], name='purchase_is_header_idx'),
            models.Index(fields=['date', 'is_header'], name='purchase_date_is_header_idx'),
            models.Index(fields=['date','po_bill_no','po_created_by'], name='purchase_date_idx'),
            models.Index(fields=['header_pur_type'], name='purchase_pur_type_idx'),
            # models.Index(fields=['is_header', 'header_net_total'], name='purchase_is_header_net_total_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_header=True, header_total_items__gte=0) |
                    models.Q(is_header=False, header_total_items=0)
                ),
                name='purchase_total_items_only_on_header',
            ),
        ]
        # unique_together = ['bill_no', 'row_no']











class PurchaseOrder(models.Model):
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
    foc_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True)
    
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    uom = models.CharField(max_length=20, blank=True, default='',null = True)
    packing_mode = models.PositiveSmallIntegerField(default=1, null=True, blank=True,
        db_comment='1=base 2=ctrn 3=dzn 4=wholesale')
    
    pack_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True,
        db_comment='crtn_qty if packing mode=2, dzn_qty if packing mode=3')
    row_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    row_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    row_net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
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
    header_payment_mode = models.IntegerField(default=112000001, null=True, blank=True,
        db_comment='112000001=cash , any other = card')
    header_cash_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_bank_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_card_last4 = models.CharField(max_length=4, blank=True, default='',null = True)
    header_total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    #======== Purchae Specific===========

    header_labour_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_freight_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_unload_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    header_freight_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    header_labour_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    header_unload_acc_code = models.IntegerField(default = 0, null=True, blank=True)
    
    # === Supplier Bill Reference - HEADER ONLY ===
    header_supl_inv_no = models.CharField(max_length=35, blank=True, default='', null=True, 
        help_text="Supplier invoice number")
    header_supl_inv_date = models.DateField(null=True, blank=True, 
        help_text="Supplier invoice date")

                        # Internal Ref - HEADER LEVEL ===
    header_our_ref = models.CharField(max_length=25, blank=True, default='', null=True,
        help_text="Our PO reference, When did we order this inovice")
    header_our_ref_date = models.DateField(null=True, blank=True)
    
    # === Foreign Currency - HEADER ONLY for most cases ===
    fc_currency = models.CharField(max_length=3, default='PKR', blank=True, null=True,
        help_text="USD, AED, CNY. PKR if local purchase")
    fc_rate = models.DecimalField(max_digits=11, decimal_places=4, default=0, null=True, blank=True,
        help_text="Exchange rate on bill date. 0 if PKR")
    fc_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True,
        help_text="Total invoice value in foreign currency")

    # If item-wise FC needed - ROW LEVEL
    row_fc_rate = models.DecimalField(max_digits=11, decimal_places=4, default=0, null=True, blank=True)
    row_fc_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)



    # === Landed Cost - ROW LEVEL ===
    row_total_cost_per_base_unit = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, blank=True,
        help_text="Landed cost per unit after freight/unload/shortage")
    row_batch_no = models.CharField(max_length=15, blank=True, default='', null=True)
    row_batch_qty = models.PositiveIntegerField(default=0, null=True, blank=True)
    row_expiry_dt = models.DateField(null=True, blank=True)
    row_pack_qty_rcvd = models.PositiveIntegerField(default=0, null=True, blank=True,
        help_text="Actually received vs pack_qty ordered")
    
    row_remaining_qty = models.PositiveIntegerField(default=0, null=True, blank=True,
        help_text="Remaining base_qty after sale")



    # === Tax - HEADER LEVEL ===
    header_wht_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True, help_text='Example: You buy goods Rs. 100,000 from an unregistered supplier. FBR rate = 4.5% WHT.header_wht_percent = 4.5header_wht_amount = 4500You pay supplier 95,500. You deposit 4,500 to FBR via CPR.')
    header_wht_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_advtax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)

    header_advtax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_gst_after_discount = models.BooleanField(default=True, 
        help_text="If False, calc GST before discount")



    # === Freight/Builty - HEADER LEVEL ===
    header_builty_no = models.CharField(max_length=15, blank=True, default='', null=True,help_text='Related to transporter')
    header_builty_date = models.DateField(null=True, blank=True)
    header_delivery_person = models.CharField(max_length=150, blank=True, default='', null=True)
    header_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    header_shortaccess = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True,
        help_text="Shortage/Access amount")

    # === Store + Status - HEADER LEVEL ===
    # store = models.ForeignKey('configuration.Store', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, default='posted', choices=[('pending','Pending'),('received','Received'),('posted','Posted')])


        # === Pricing - ROW LEVEL ===
    row_trade_price = models.DecimalField(max_digits=12, decimal_places=4, default=0, null=True, blank=True,
        help_text="Trade Price,What you sell")
    row_actual_retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True,
        help_text="Retail Price") 
    row_oldcost = models.DecimalField(max_digits=18, decimal_places=4, default=0, null=True, blank=True,
        help_text="Previous cost for profit calc")

    # === Extra Discounts - ROW LEVEL ===
    row_discount_percent2 = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    row_discount_amount2 = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    # row_bonus = models.DecimalField(max_digits=12, decimal_places=3, default=0, null=True, blank=True,
    #     help_text="Free bonus qty")
    row_bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)

    
    
    header_pur_type = models.CharField(max_length=50, default='p', null=True, blank=True, help_text="purchase=p, purchase_return=pr, purchase_order=po, consignment_in=cin")
    
    class Meta:
        managed = True
        db_table = 'purchase_order'
        indexes = [
            models.Index(fields=['bill_no'], name='po_bill_no_idx'),
            models.Index(fields=['is_header'], name='po_is_header_idx'),
            models.Index(fields=['date', 'is_header'], name='po_date_is_header_idx'),
            models.Index(fields=['date'], name='po_date_idx'),
            models.Index(fields=['header_pur_type'], name='po_pur_type_idx'),
            # models.Index(fields=['is_header', 'header_net_total'], name='purchase_order_is_header_net_total_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_header=True, header_total_items__gte=0) |
                    models.Q(is_header=False, header_total_items=0)
                ),
                name='po_total_items_only_on_header',
            ),
        ]
        # unique_together = ['bill_no', 'row_no']

