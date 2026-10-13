from django.db import models

# Create your models here.


class ItemBrand(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name


class ItemCompany(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name


class ItemCategory(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

class ItemSubCategory(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

class ItemType(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

class Unit(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    
class Location(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name




def product_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    # company/branch sharding to avoid 10k files in one folder
    return f"items/{instance.company_id}/{instance.branch_id}/{instance.inv_id}.{ext}"



class Inventory(models.Model):
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, default=None)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, default=None)

    inv_id = models.AutoField(primary_key=True)

    prod_name = models.CharField(max_length=255, default=None)
    prod_name_ur = models.CharField(
        max_length=500, null=True, blank=True, default=None,
        verbose_name="Urdu Item Name",
        help_text="آئٹم کا اردو نام — Nastaleeq font will be used in Urdu/Bilingual invoices.",
    )
    alias_name = models.CharField(max_length=255, null=True, blank=True, default=None)

    prod_picture = models.ImageField(upload_to=product_image_path, null=True, blank=True, max_length=500)
    prod_picture_thumb = models.ImageField(upload_to=product_image_path, null=True, blank=True, max_length=500,
                                           help_text="Auto generated 150x150 webp")
    image_updated_at = models.DateTimeField(null=True, blank=True)

    ws_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    ws_disc_per = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=None)

    market_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    last_pur_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)

    base_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    base_uom = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='base_inv')
    base_disc_per = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=None)
    min_base_sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)

    carton_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    carton_uom = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='carton_inv')
    carton_qty = models.IntegerField(null=True, blank=True, default=None)
    carton_disc_per = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=None)

    dzn_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=None)
    dzn_uom = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='dzn_inv')
    dzn_qty = models.IntegerField(null=True, blank=True, default=None)
    dzn_disc_per = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=None)

    date = models.DateField(null=True, blank=True, default=None)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.CharField(max_length=100, null=True, blank=True, default=None)
    updated_by = models.CharField(max_length=100, null=True, blank=True, default=None)

    barcode = models.CharField(max_length=255, null=True, blank=True, default=None)
    manualbc = models.CharField(max_length=255, null=True, blank=True, default=None)
    barcode2 = models.CharField(max_length=255, null=True, blank=True, default=None)

    manufacturer = models.ForeignKey(ItemCompany, on_delete=models.CASCADE ,null=True,blank=True,default=None)
    brand = models.ForeignKey(ItemBrand, on_delete=models.CASCADE ,null=True,blank=True,default=None)
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE ,null=True,blank=True,default=None)
    subcategory = models.ForeignKey(ItemSubCategory, on_delete=models.CASCADE ,null=True,blank=True,default=None)

    active = models.BooleanField(null=True, blank=True, default=True)
    is_deleted = models.BooleanField(null=True, blank=True, default=False)


    min_stock = models.IntegerField(null=True, blank=True, default=None)
    max_stock = models.IntegerField(null=True, blank=True, default=None)
    reorder = models.IntegerField(null=True, blank=True, default=None)

    product_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, default=None)

    expiry_date = models.DateField(null=True, blank=True, default=None)

    remaining_qty = models.IntegerField(null=True, blank=True, default=None)

    bal_qty = models.IntegerField(null=True, blank=True, default=0)
    # last_pur_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)


    salesman_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
        
    # Medicine-specific information
    salt_composition = models.CharField(max_length=255, null=True, blank=True)
    generic_group = models.CharField(max_length=150, null=True, blank=True, db_index=True)
    strength = models.CharField(max_length=100, null=True, blank=True)
    
    # Regulatory information
    registration_no = models.CharField(max_length=100, null=True, blank=True)
    schedule_type = models.CharField(
        max_length=30,
        choices=[
            ('GENERAL', 'General'),
            ('PRESCRIPTION', 'Prescription Required'),
            ('CONTROLLED', 'Controlled Medicine'),
            ('SCHEDULE_B', 'Schedule B'),
            ('SCHEDULE_G', 'Schedule G'),
        ],
        default='GENERAL',
        null= True,
        blank=True,
        
    )    
    is_narcotic = models.BooleanField(default=False)


    # not in use fields to prevent any changes
    sold_qty = models.IntegerField(null=True, blank=True, default=None)
    sold_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    purchase_qty = models.IntegerField(null=True, blank=True, default=None)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)


    def __str__(self):
        return self.prod_name or f"Product {self.inv_id}"

    class Meta:
        indexes = [
            models.Index(fields=['company', 'barcode'], name='idx_inv_comp_bar'),
            models.Index(fields=['company', 'manualbc'], name='idx_inv_comp_mbc'),
            models.Index(fields=['company', 'barcode2'], name='idx_inv_comp_b2'),
            models.Index(fields=['company', 'inv_id'], name='idx_inv_comp_invid'),
            models.Index(fields=['company', 'alias_name'], name='idx_inv_comp_alias'),
            models.Index(fields=['company', 'prod_name'], name='idx_inv_comp_prod'),
        ]







class StockLot(models.Model):
    """The REAL stock. One row = one purchase batch. Qty tracking for all 5 methods."""
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, db_index=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, db_index=True)
    
    # Meaningful name: inventory_item_id = inv_id
    inventory_item = models.ForeignKey(
        Inventory, 
        on_delete=models.CASCADE, 
        db_index=True, 
        db_column='item_id',
        related_name='stock_lots'
    )

    # qty = qty * pack_qty
    quantity_received = models.DecimalField(max_digits=12, decimal_places=3, db_column='qty_received')
    quantity_remaining = models.DecimalField(max_digits=12, decimal_places=3, db_index=True, db_column='qty_remaining')
    
    # rate_cost = row_total_cost_per_base_unit
    rate_cost_per_unit = models.DecimalField(max_digits=12, decimal_places=4, db_column='unit_cost')

    # row_expiry_dt
    expiry_date = models.DateField(null=True, blank=True, db_index=True, db_column='expiry_date')
    
    # header date
    receipt_date = models.DateField(db_index=True, db_column='receipt_date')
    
    
    batch_no = models.CharField(max_length=50, db_index=True, db_column='batch_no',null=True,blank=True) # PURCHASE, SALE

    # Source - meaningful names
    source_voucher_type = models.CharField(max_length=20, db_index=True, db_column='source_type') # PURCHASE, SALE, OPENING
    source_bill_no = models.IntegerField(db_index=True, db_column='source_id') # bill_no
    acc_code = models.IntegerField(db_index=True, db_column='acc_code',null=True,blank=True) # acc_code for accounting
    source_row_id = models.BigIntegerField(null=True, db_column='source_line_id') # Purchase.id / Invoice.id

    dateent = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_lot'
        indexes = [
            models.Index(fields=['company', 'branch', 'inventory_item', 'receipt_date', 'id'], name='idx_lot_fifo'),
            models.Index(fields=['company', 'branch', 'inventory_item', 'expiry_date', 'receipt_date'], name='idx_lot_fefo'),
        ]

    def __str__(self):
        return f"Lot {self.id} - {self.inventory_item.prod_name} - Rem {self.quantity_remaining}/{self.quantity_received}"

class StockLedger(models.Model):
    """Immutable history for 5 valuations. NEVER update. Only INSERT and REVERSE."""
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, db_index=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, db_index=True)
    
    inventory_item = models.ForeignKey(
        Inventory, 
        on_delete=models.CASCADE, 
        db_index=True, 
        db_column='item_id',
        related_name='stock_ledgers'
    )

    stock_lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, null=True, db_column='lot_id')

    # qty: + for IN, - for OUT
    base_quantity = models.DecimalField(max_digits=12, decimal_places=3, db_column='qty')
    
    rate_cost_per_unit = models.DecimalField(max_digits=12, decimal_places=4, db_column='unit_cost')
    net_value = models.DecimalField(max_digits=15, decimal_places=2, db_column='value') # base_quantity * rate_cost

    # Voucher reference - meaningful names
    voucher_type = models.CharField(max_length=20, db_index=True, db_column='ref_type') # PURCHASE, SALE
    batch_no = models.CharField(max_length=50, db_index=True, db_column='batch_no',null=True,blank=True) # PURCHASE, SALE
    voucher_bill_no = models.IntegerField(db_index=True, db_column='ref_id') # bill_no
    voucher_row_id = models.BigIntegerField(null=True, db_column='ref_line_id') # Invoice.id / Purchase.id


    acc_code = models.IntegerField(db_index=True, db_column='acc_code',null=True,blank=True) # acc_code for accounting
    
    
    adj_type = models.CharField(max_length=20, null=True,blank = True,db_column='adj_type' ,default= '') # OPENING, DAMAGE, LEAKAGE
    voucher_date = models.DateField(db_index=True, db_column='date')
    dateent = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_ledger'
        indexes = [
            models.Index(fields=['voucher_type', 'voucher_bill_no'], name='idx_led_voucher'),
            models.Index(fields=['company', 'branch', 'inventory_item', 'voucher_date'], name='idx_led_item_date'),
        ]

    def __str__(self):
        return f"{self.voucher_type} {self.voucher_bill_no} - {self.base_quantity}"
    
    
    
    
    


# -- Add this once in mysql for full text index in mysql
# ALTER TABLE inventory_inventory ADD FULLTEXT(prod_name, alias_name);


# class StockLot(models.Model):
#     """The REAL stock. One row = one purchase/opening batch."""
#     company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
#     branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
#     item = models.ForeignKey(Inventory, on_delete=models.CASCADE, db_index=True)

#     qty_received = models.DecimalField(max_digits=12, decimal_places=3)
#     qty_remaining = models.DecimalField(max_digits=12, decimal_places=3, db_index=True)
#     unit_cost = models.DecimalField(max_digits=12, decimal_places=4)

#     expiry_date = models.DateField(null=True, blank=True, db_index=True)
#     receipt_date = models.DateField(db_index=True)
    
#     # Where this lot came from
#     source_type = models.CharField(max_length=20, db_index=True) # OPENING, PURCHASE, ADJUSTMENT_IN
#     source_id = models.IntegerField() # id of voucher
#     source_line_id = models.IntegerField(null=True)

#     dateent = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'stock_lot'
#         indexes = [
#             models.Index(fields=['company', 'branch', 'item', 'receipt_date', 'id']),
#             models.Index(fields=['company', 'branch', 'item', 'expiry_date', 'receipt_date']),
#         ]

# class StockLedger(models.Model):
#     """Immutable history. NEVER update/delete. Only INSERT and REVERSE."""
#     company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
#     branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
#     item = models.ForeignKey(Inventory, on_delete=models.CASCADE)

#     lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, null=True)
#     qty = models.DecimalField(max_digits=12, decimal_places=3) # +10 / -5
#     unit_cost = models.DecimalField(max_digits=12, decimal_places=4)
#     value = models.DecimalField(max_digits=15, decimal_places=2)

#     ref_type = models.CharField(max_length=20, db_index=True) # PURCHASE, SALE, ADJUSTMENT, OPENING
#     ref_id = models.IntegerField(db_index=True) # Voucher Header ID
#     ref_line_id = models.IntegerField(null=True)

#     date = models.DateField(db_index=True)
#     dateent = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'stock_ledger'
        
        
        
        
        

# class StockAdjustment(models.Model):
#     ADJUSTMENT_TYPES = [
#         ('OPENING', 'Opening'),
#         ('DESTROYED_EXPIRED', 'Destroyed/Expired'),
#         ('SAMPLE_GIVEN', 'Sample Given'),
#         ('BREAKAGE_LEAKAGE', 'Breakage/Leakage'),
#         ('THEFT_SHORTAGE', 'Theft/Shortage'),
#         ('EXCESS_FOUND', 'Excess Found'),
#         ('CORRECTION', 'Correction'),
#     ]

#     company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
#     branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
#     voucher_no = models.IntegerField(null=True, blank=True)
    
#     item = models.IntegerField()
#     category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True)
#     subcategory = models.ForeignKey(ItemSubCategory, on_delete=models.SET_NULL, null=True, blank=True)
#     location = models.CharField(max_length=255, null=True, blank=True)
    
#     qty = models.DecimalField(max_digits=12, decimal_places=3, default=0)
#     pack_qty = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    
#     rate_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
#     net_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
#     adj_type = models.CharField(max_length=50, choices=ADJUSTMENT_TYPES)
#     acc_code = models.IntegerField(null=True, blank=True)
#     reason = models.CharField(max_length=255, null=True, blank=True)
    
#     date = models.DateField(db_index=True)
#     dateent = models.DateTimeField(auto_now_add=True)
#     user = models.CharField(max_length=150, null=True, blank=True)

#     class Meta:
#         db_table = 'stock_adjustment'
#         indexes = [
#             models.Index(fields=['company', 'voucher_no']),
#             models.Index(fields=['company', 'date']),
#         ]
