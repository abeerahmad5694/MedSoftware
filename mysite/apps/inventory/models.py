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


    
    # ============================================================
    # === NEW FIELDS FOR LAPTOP / MOBILE / AUTO / TECH SHOP ===
    # ============================================================

    # --- A. Tracking Type - What kind of product is this? ---
    # Purpose: System will know how to handle stock
    # Example:
    #   NONE = Mouse, Charger, Keyboard - Simple qty stock like 50 pcs
    #   SERIAL = Laptop, Mobile, Car - Each piece has unique Serial/IMEI/Chassis, qty always 1
    TRACKING_CHOICES = [
        ('NONE', 'Simple Item - Qty Based'),
        ('SERIAL', 'Serial / IMEI / Chassis Based'),
    ]
    tracking_type = models.CharField(
        max_length=10, 
        choices=TRACKING_CHOICES, 
        default='NONE',
        null=True, blank=True,
        help_text="NONE for Accessories, SERIAL for Laptop/Mobile/Car"
    )

    # --- B. Parent-Child Linking - For Variants ---
    # Purpose: To group variants under one main product
    # Real Example:
    #   Parent: inv_id 100, prod_name="【entity-Dell¦canonical_name=Dell】 Inspiron 3530" (No stock, only for grouping)
    #   Child 1: inv_id 101, parent_item=100, prod_name="【entity-Dell¦canonical_name=Dell】 Inspiron 3530 i5 8GB" (Real stock with serial)
    #   Child 2: inv_id 102, parent_item=100, prod_name="【entity-Dell¦canonical_name=Dell】 Inspiron 3530 i7 16GB" (Real stock with serial)
    #   When user searches "Inspiron", you show all childs of parent 100
    parent_item = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='variants',
        help_text="If this is variant, select its main parent product"
    )
    is_variant = models.BooleanField(default=False, help_text="True if this row is a variant/serial piece")
    variant_title = models.CharField(max_length=200, null=True, blank=True, help_text="e.g. i5 8GB 512GB Silver / 128GB Black")

    # --- C. Generic Variant Specs - Works for all businesses ---
    # Purpose: Store specs without creating separate tables
    # For Laptop: processor=i5 12th, ram=16GB, storage=512GB SSD
    # For Mobile: storage=128GB, ram=8GB, color=Black
    # For Car: You can use color=White, storage=1800cc (engine), processor=Altis 1.6
    # For Accessories: Leave blank
    processor = models.CharField(max_length=100, null=True, blank=True, help_text="Laptop: i5 12th / Mobile: Snapdragon 8 Gen 2 / Car: Altis 1.6")
    ram = models.CharField(max_length=20, null=True, blank=True, help_text="Laptop/Mobile RAM: 8GB, 16GB")
    storage = models.CharField(max_length=50, null=True, blank=True, help_text="Laptop: 512GB SSD / Mobile: 128GB / Car: 1800cc")
    color = models.CharField(max_length=50, null=True, blank=True, help_text="Common for all: Black, Silver, White")
    model_year = models.CharField(max_length=10, null=True, blank=True, help_text="For Car: 2024, For Laptop: 2024 Model")

    # --- D. Serial / IMEI / Chassis Tracking - Most Important ---
    # Purpose: Each physical piece has unique identity
    # Real Examples:
    #   Laptop: serial_no = "SN-DL-12345" (Laptop Serial), serial_no2 = "" (empty)
    #   Mobile: serial_no = "352751234567890" (IMEI 1), serial_no2 = "352751234567891" (IMEI 2)
    #   Car: serial_no = "CH-MT-123456" (Chassis No), serial_no2 = "EN-987654" (Engine No)
    #   Accessories: Leave blank
    serial_no = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="Laptop SN / Mobile IMEI 1 / Car Chassis No")
    serial_no2 = models.CharField(max_length=100, null=True, blank=True, help_text="Mobile IMEI 2 / Car Engine No")
    # To prevent duplicate serial entry
    # class Meta:
    #     # ... keep your existing indexes and add this:
    #     # You will add this constraint after migration, for now just in comment
    #     # constraints = [ models.UniqueConstraint(fields=['company', 'serial_no'], condition=Q(serial_no__isnull=False), name='uniq_serial_per_company') ]
    #     indexes = [
    #         models.Index(fields=['company', 'barcode'], name='idx_inv_comp_bar'),
    #         models.Index(fields=['company', 'manualbc'], name='idx_inv_comp_mbc'),
    #         models.Index(fields=['company', 'barcode2'], name='idx_inv_comp_b2'),
    #         models.Index(fields=['company', 'inv_id'], name='idx_inv_comp_invid'),
    #         models.Index(fields=['company', 'alias_name'], name='idx_inv_comp_alias'),
    #         models.Index(fields=['company', 'prod_name'], name='idx_inv_comp_prod'),
    #         models.Index(fields=['company', 'serial_no'], name='idx_inv_comp_serial'), # NEW
    #         models.Index(fields=['company', 'parent_item'], name='idx_inv_comp_parent'), # NEW
    #     ]

    # --- E. Condition & Status - For Used / Refurb / Repair ---
    # Purpose: Track where is the piece and what is its quality
    # Real Examples:
    #   condition: NEW = Box Pack, USED = Customer used, REFURB = Repaired and ready, FAULTY = Damaged
    #   status: IN_STOCK = Ready for sale (Show in POS), SOLD = Sold out, IN_REPAIR = In workshop (Don't show in POS), DAMAGED = Faulty
    CONDITION_CHOICES = [
        ('NEW', 'New - Box Pack'),
        ('USED', 'Used - Direct Purchase'),
        ('REFURB', 'Refurbished'),
        ('FAULTY', 'Faulty / Damaged'),
    ]
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock - Ready to Sale'),
        ('SOLD', 'Sold'),
        ('IN_REPAIR', 'In Workshop / Repair'),
        ('RESERVED', 'Reserved for Customer'),
        ('DAMAGED', 'Damaged - Not for Sale'),
    ]
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='NEW', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='IN_STOCK', null=True, blank=True)

    # --- F. Costing - Real Profit Calculation ---
    # Purpose: Each serial piece has its own cost, not average
    # Real Example:
    #   You buy 2 same laptops: SN-001 for 150k, SN-002 for 145k (different shipment)
    #   If you use average cost, profit will be wrong. So we store cost per piece.
    #   individual_cost = What you paid to supplier/customer
    #   extra_cost = What you spent after buying (RAM upgrade, repair, paint)
    #   final_cost = individual_cost + extra_cost (Real cost for profit)
    individual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Buying price of this single piece")
    extra_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, help_text="Repair / Upgrade cost spent after purchase")

    # @property
    # def final_cost(self):
    #     # Real cost for profit calculation
    #     return (self.individual_cost or 0) + (self.extra_cost or 0)

    # --- G. Warranty ---
    # Purpose: Track warranty per serial piece
    # Real Example: Laptop SN-001 Warranty till 2026-05-01, Mobile IMEI till 2025-12-01
    warranty_start = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    
    
    
    @property
    def final_cost(self):
        # Real cost = Buying + Extra spent
        # Example: 80k + 15k = 95k
        return (self.individual_cost or 0) + (self.extra_cost or 0)
    def __str__(self):
        if self.is_variant and self.serial_no:
            return f"{self.prod_name} - {self.serial_no}"
        return self.prod_name or f"Product {self.inv_id}"
    class Meta:
        # ONE Meta only - Fixed
        indexes = [
            models.Index(fields=['company', 'barcode'], name='idx_inv_comp_bar'),
            models.Index(fields=['company', 'manualbc'], name='idx_inv_comp_mbc'),
            models.Index(fields=['company', 'barcode2'], name='idx_inv_comp_b2'),
            models.Index(fields=['company', 'inv_id'], name='idx_inv_comp_invid'),
            models.Index(fields=['company', 'alias_name'], name='idx_inv_comp_alias'),
            models.Index(fields=['company', 'prod_name'], name='idx_inv_comp_prod'),
            models.Index(fields=['company', 'serial_no'], name='idx_inv_comp_serial'),
            models.Index(fields=['company', 'parent_item'], name='idx_inv_comp_parent'),
        ]
    





class ItemExpense(models.Model):
    """
    Purpose: Track every extra rupee spent on a single serial piece
    Real Example: 
      Laptop SN-001 bought for 80k (USED)
      Expense 1: Battery 7000
      Expense 2: 8GB RAM 6000
      Expense 3: Servicing 2000
      Total extra_cost = 15000
      Final cost = 95000
    """
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='expenses', help_text="Which serial piece this expense is for")
    
    expense_type = models.CharField(max_length=100, help_text="e.g. RAM Upgrade, Battery, SSD, Denting, Painting, Servicing")
    description = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    # Link to Gledg for accounting
    gledg_ref = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.inventory_item.serial_no} - {self.expense_type} - {self.amount}"
    
    



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
    
    
    
    