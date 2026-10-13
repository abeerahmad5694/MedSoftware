from django.db import models

# Create your models here.
class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
    name_ur = models.CharField(max_length=200, blank=True, null=True, verbose_name="Company Name (Urdu)")
    address = models.CharField(max_length=255, blank=True, null=True)
    address_ur = models.CharField(max_length=500, blank=True, null=True, verbose_name="Address (Urdu)")
    phone1 = models.CharField(max_length=15, blank=True, null=True)
    phone2 = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    license_no = models.CharField(max_length=50, blank=True, null=True)
    ntn_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="NTN Number")
    ntn_no_ur = models.CharField(max_length=100, blank=True, null=True, verbose_name="NTN Number (Urdu)")
    license_expiry = models.DateField(null=True, blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField(max_length=100)
    name_ur = models.CharField(max_length=200, blank=True, null=True, verbose_name="Branch Name (Urdu)")
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    address_ur = models.CharField(max_length=500, blank=True, null=True, verbose_name="Address (Urdu)")
    phone1 = models.CharField(max_length=15, blank=True, null=True)
    phone2 = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    license_no = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to='branch_logos/', blank=True, null=True)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name

class POSTerminal(models.Model):
    name = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    class Meta:
        unique_together = ('name', 'branch')



class CompanyConfiguration(models.Model):
    RECEIPT_CHOICES = [
        ('Thermal', 'Thermal'),
        ('A4', 'A4'),
        ('A5', 'A5'),
    ]
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)
    
    # Legacy fields for backward compatibility
    promotion_disc_percent_bill = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    promotion_disc_percent_item = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    multiple_bill_prints = models.IntegerField(default=1)

    pos_sale_receipt_size = models.CharField(max_length=10, choices=RECEIPT_CHOICES, default='Thermal')
    credit_sale_receipt_size = models.CharField(max_length=10, choices=RECEIPT_CHOICES, default='Thermal')
    purchase_receipt_size = models.CharField(max_length=10, choices=RECEIPT_CHOICES, default='Thermal')
    VALUATION_METHOD_CHOICES = [
        ('FIFO', 'FIFO (First In, First Out)'),
        ('FEFO', 'FEFO (First Expired, First Out)'),
        ('LIFO', 'LIFO (Last In, First Out)'),
        ('AVERAGE', 'Weighted Average Cost'),
        ('LAST_PUR_PRICE', 'Last Purchase Price'),
    ]
    stock_valuation_method = models.CharField(
        max_length=20,
        choices=VALUATION_METHOD_CHOICES,
        default='LAST_PUR_PRICE',
        help_text="Stock valuation method for COGS and inventory lot consumption"
    )

    # Ultra-fast flexible JSON configuration per module
    config_data = models.JSONField(default=dict, blank=True, help_text="Module-wise JSON configuration: {'pos': {...}, 'purchase': {...}, 'quotation': {...}, 'inventory': {...}, 'general': {...}}")

    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'branch')
        verbose_name = 'Company Configuration'
        verbose_name_plural = 'Company Configurations'

    def get_setting(self, module, key, default=None):
        if not self.config_data or not isinstance(self.config_data, dict):
            return default
        module_dict = self.config_data.get(module, {})
        if isinstance(module_dict, dict):
            return module_dict.get(key, default)
        return default

    def set_setting(self, module, key, value):
        if not isinstance(self.config_data, dict):
            self.config_data = {}
        if module not in self.config_data or not isinstance(self.config_data[module], dict):
            self.config_data[module] = {}
        self.config_data[module][key] = value

    def __str__(self):
        return f'{self.company.name} ({self.branch.name}) Configuration'


class DefaultAccounts(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)

    # Ultra-fast flexible JSON configuration for Default Chart of Accounts
    accounts_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key-value mapping of default accounts: {'cash_client_acc': 112000001, 'sales_counter_acc': 110000001, ...}"
    )

    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('company', 'branch')
        verbose_name = 'Default Accounts Configuration'
        verbose_name_plural = 'Default Accounts Configurations'

    def get_account_code(self, key, default=None):
        if not self.accounts_data or not isinstance(self.accounts_data, dict):
            return default
        return self.accounts_data.get(key, default)

    def set_account_code(self, key, acc_code):
        if not isinstance(self.accounts_data, dict):
            self.accounts_data = {}
        self.accounts_data[key] = acc_code

    def __str__(self):
        return f'{self.company.name} ({self.branch.name}) - Default Accounts'
    