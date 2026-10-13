from django.db import models
from django.db.models import IntegerField, FloatField, CharField, TextField, DateField

class Accounts(models.Model):

    # Basic Keys
    ID = models.CharField(db_column='id', max_length=1, null=True, blank=True)
    BRANCH_ID = models.IntegerField(db_column='branchid', null=True, blank=True)
    SERIAL_NO = models.IntegerField(db_column='serialno', null=True, blank=True)

    ACC_CODE = models.IntegerField(db_column='acc_code', primary_key=True)

    # Account Control
    FIXED_HEAD = models.CharField(db_column='fixedhead', max_length=1, null=True, blank=True)
    ENABLE = models.CharField(db_column='enable', max_length=1, null=True, blank=True)
    BUDGET = models.CharField(db_column='budget', max_length=1, null=True, blank=True)

    # Core Info
    ACC_NAME = models.CharField(db_column='head', max_length=70, null=True, blank=True)
    ADDRESS = models.CharField(db_column='address', max_length=80, null=True, blank=True)

    COUNTRY = models.CharField(db_column='country', max_length=45, null=True, blank=True)
    CITY = models.CharField(db_column='city', max_length=20, null=True, blank=True)

    # Contact Info
    PHONE_OFF = models.CharField(db_column='phone_off', max_length=30, null=True, blank=True)

    PHONE_RES = models.CharField(db_column='phone_res', max_length=15, null=True, blank=True)
    MOBILE_NO = models.CharField(db_column='mobile_no', max_length=40, null=True, blank=True)

    WEB_ADDRESS = models.CharField(db_column='web_add', max_length=40, null=True, blank=True)
    EMAIL_ADDRESS = models.CharField(db_column='email_add', max_length=40, null=True, blank=True)

    NAME_OF_HEAD = models.CharField(db_column='nameofhead', max_length=70, null=True, blank=True)

    # Classification
    LEVEL = models.IntegerField(db_column='level', null=True, blank=True)
    TYPE = models.CharField(db_column='type', max_length=6, null=True, blank=True)
    CLASS_FIELD = models.CharField(db_column='class', max_length=18, null=True, blank=True)

    # Financial
    OPENING_BALANCE = models.FloatField(db_column='op_balance', null=True, blank=True, default=0.00)
    BALANCE_TYPE = models.CharField(db_column='bal_type', max_length=2, null=True, blank=True)

    REMARKS = models.TextField(db_column='remarks', null=True, blank=True)

   
    REF_CODE = models.IntegerField(db_column='ref_code', null=True, blank=True)

    CREDIT_LIMIT = models.IntegerField(db_column='crlimit', null=True, blank=True)
   
    BANK_ACCOUNT = models.IntegerField(db_column='bank_acct', null=True, blank=True)

    PICTURE = models.CharField(db_column='pict_upload', max_length=20, null=True, blank=True)

    BANK_RECONCILE = models.CharField(db_column='bank_reconcile', max_length=1, null=True, blank=True)

    # LOCKED = models.BooleanField(default = False)
    PASSWORD = models.CharField(db_column='acc_pwd', max_length=10, null=True, blank=True)
    
    RECONCILE_DATE = models.DateField(db_column='reconcile_dte', null=True, blank=True)
    RECONCILE_REMARKS = models.CharField(db_column='reconcile_rmks', max_length=50, null=True, blank=True)

    PROFILE_DISCOUNT = models.CharField(db_column='profile_disc', max_length=1, null=True, blank=True, default='N')

    SALESMAN = models.CharField(db_column='salesman', max_length=25, null=True, blank=True)

    NTN_NO = models.CharField(db_column='ntnno', max_length=35, null=True, blank=True)
    STN_NO = models.CharField(db_column='stnno', max_length=35, null=True, blank=True)

    BRANCH = models.ForeignKey('configuration.Branch',db_column="branch", default=1, null=True, blank=True, on_delete=models.CASCADE)
    POSTERMINAL = models.ForeignKey('configuration.POSTerminal',db_column="terminal", default=1, null=True, blank=True, on_delete=models.CASCADE)
    COMPANY = models.ForeignKey('configuration.Company',db_column="company", default=1, null=True, blank=True, on_delete=models.CASCADE)



    RECONCILE_DATE = models.DateField(null=True, blank=True ,db_column = 'reconcile_dte')
    DATEENT = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    DATEEDIT = models.DateTimeField(auto_now=True, null=True, blank=True)

    USER = models.CharField(max_length=100, null=True, blank=True)
    EDITBY = models.CharField(max_length=100, null=True, blank=True) 


    def save(self):
        if self.BRANCH is None:
            self.BRANCH = Branch.objects.get(branch_name="Main Branch")
        if self.POSTERMINAL is None:
            self.POSTERMINAL = POSTerminal.objects.get(terminal_name="Main Terminal")
        if self.COMPANY is None:
            self.COMPANY = Company.objects.get(company_name="Main Company")
        super().save()

    # =========================================================
    # EXTRA TABLE FIELDS (NOT USED CURRENTLY)
    # =========================================================

    # FAX = models.CharField(db_column='fax', max_length=30, null=True, blank=True)

    # INV_SUB = models.CharField(db_column='inv_sub', max_length=25, null=True, blank=True)

    # CREDIT_DAYS = models.IntegerField(db_column='credit_days', null=True, blank=True)

    # PAYMENT_DATE = models.DateField(db_column='payment_date', null=True, blank=True)

    # APP_DATE = models.DateField(db_column='app_date', null=True, blank=True)

    # EXIT_DATE = models.DateField(db_column='exit_date', null=True, blank=True)

    # DEPARTMENT = models.CharField(db_column='department', max_length=50, null=True, blank=True)

    # SUB_DEPT = models.CharField(db_column='sub_dept', max_length=45, null=True, blank=True)

    # DESIGNATION = models.CharField(db_column='designation', max_length=50, null=True, blank=True)

    # BASIC_SALARY = models.IntegerField(db_column='basic_salary', null=True, blank=True)

    # ALLOW1 = models.IntegerField(db_column='allow1', null=True, blank=True)

    # ALLOW2 = models.IntegerField(db_column='allow2', null=True, blank=True)

    # ALLOW3 = models.IntegerField(db_column='allow3', null=True, blank=True)

    # DEDUCTION1 = models.IntegerField(db_column='deduction1', null=True, blank=True)

    # DEDUCTION2 = models.IntegerField(db_column='deduction2', null=True, blank=True)

    # REST_DAY = models.CharField(db_column='rest_day', max_length=10, null=True, blank=True)

    # CNIC_NO = models.CharField(db_column='cnic_no', max_length=15, null=True, blank=True)

    # PAYABLE = models.IntegerField(db_column='payable', null=True, blank=True)

    # SALARY_BLOCK = models.CharField(db_column='salary_block', max_length=1, null=True, blank=True)

    # INST_PER_MNTH = models.IntegerField(db_column='inst_per_mnth', null=True, blank=True)

    # ADVOPBAL = models.IntegerField(db_column='advopbal', null=True, blank=True)

    # LOANOPBAL = models.IntegerField(db_column='loanopbal', null=True, blank=True)

    # PROBATION_DT = models.DateField(db_column='probation_dt', null=True, blank=True)

    # CHKADV_DED = models.IntegerField(db_column='chkadv_ded', null=True, blank=True)

    # CHKLOAN_DED = models.IntegerField(db_column='chkloan_ded', null=True, blank=True)

    # SHIFTTIME = models.CharField(db_column='shifttime', max_length=7, null=True, blank=True)

    # DUTY_END = models.CharField(db_column='duty_end', max_length=8, null=True, blank=True)

    # DUTY_START = models.CharField(db_column='duty_start', max_length=8, null=True, blank=True)

    # BANK_PAY = models.CharField(db_column='bank_pay', max_length=1, null=True, blank=True)

    # DUTYNEXTDAY = models.IntegerField(db_column='dutynextday', null=True, blank=True)

    # WORKHRDAY = models.IntegerField(db_column='workhrday', null=True, blank=True)

    # REST_DAY1 = models.CharField(db_column='rest_day1', max_length=10, null=True, blank=True)

    def save(self, *args, **kwargs):

        for field in self._meta.fields:
    
            value = getattr(self, field.name)

            # HANDLE NULL / EMPTY VALUES
            if value in [None, '', 'NULL', 'null']:

                # INTEGER
                if isinstance(field, IntegerField):

                    # PRIMARY KEY SHOULD NOT AUTO ZERO
                    if field.primary_key:
                        continue

                    setattr(self, field.name, 0)

                # FLOAT
                elif isinstance(field, FloatField):
                    setattr(self, field.name, 0.0)

                # CHAR / TEXT
                elif isinstance(field, (CharField, TextField)):
                    setattr(self, field.name, ' ')

                # DATE
                elif isinstance(field, DateField):
                    setattr(self, field.name, '1900-01-01')

        super().save(*args, **kwargs)

    class Meta:
        db_table = "accounts"
        indexes = [
            models.Index(fields=['LEVEL', 'CLASS_FIELD', 'TYPE']),
            models.Index(fields=['ACC_CODE']),
            models.Index(fields=['COMPANY', 'ACC_CODE'], name='idx_acc_comp_code'),
            models.Index(fields=['COMPANY', 'ACC_NAME'], name='idx_acc_comp_name'),
        ]
        
    def __str__(self):
        return str(self.ACC_CODE)