from django.db import models
from django.db.models import IntegerField, FloatField, CharField, TextField,DateTimeField, DateField

# Create your models here.

class Gledg(models.Model):

    GLEDG_ID = models.AutoField(primary_key=True, db_column="gledg_id")

    ACC_CODE = models.IntegerField(db_column="acc_code", null=True, blank=True)
    REF_ACC_CODE = models.IntegerField(db_column="ref_acc_code")
    ACC_HEAD = models.CharField(max_length=200, db_column="acc_head", null=True, blank=True)

    V_TYPE = models.CharField(db_column="v_type", max_length=2, null=True, blank=True)
    VNO = models.IntegerField(db_column="vno", null=True, blank=True)

    DATE = models.DateField(db_column="date", null=True, blank=True)

    DESCRIPTION = models.CharField(db_column="desc", max_length=60, null=True, blank=True)
    REMARKS = models.CharField(db_column="remarks", max_length=60, null=True, blank=True)

    AMOUNT = models.DecimalField(db_column="amount", max_digits=12, decimal_places=2, null=True, blank=True)
    AMT_TYPE = models.CharField(db_column="amt_type", max_length=2, null=True, blank=True)

    CHQNO = models.CharField(db_column="chqno", max_length=15, null=True, blank=True)

    PUR_INV = models.CharField(
        db_column="Pur_Inv",
        max_length=1,
        default='I',
        null=True,
        blank=True,
        help_text="R = Production, P = Purchase, I = Invoice"
    )

    DATEENT = models.DateTimeField(db_column="dateent", null=True, blank=True)
    DATEEDIT = models.DateTimeField(db_column="dateedit", null=True, blank=True)

    USER = models.CharField(db_column="user", max_length=10, null=True, blank=True)
    EDITBY = models.CharField(db_column="editby", max_length=10, null=True, blank=True)


    RECEIPTNO = models.IntegerField(db_column="receiptno", null=True, blank=True)
    INVOICE_ID = models.IntegerField(db_column="inv_id", null=True, blank=True)

    SHIFT = models.CharField(db_column="shift", max_length=1, null=True, blank=True)

    CHEQUE_DATE = models.DateField(db_column="cheque_date", null=True, blank=True)

    DRAWN_BRANCH = models.CharField(db_column="drawn_branch", max_length=35, null=True, blank=True)

    PAYMENTMETHOD = models.CharField(db_column="paymentmethod", max_length=12, null=True, blank=True)

    SHOW_IN_SALE_RPT = models.CharField(
        db_column="show_in_sale_rpt",
        max_length=1,
        default='N'
    )

    BANK_RECONCILE = models.CharField(db_column="bank_reconcile", max_length=1, null=True, blank=True)

    ISPOSTED = models.CharField(db_column="isposted", max_length=1, null=True, blank=True)

    SALES_MAN = models.CharField(db_column="sales_man", max_length=15, null=True, blank=True)

    BRANCH = models.ForeignKey('configuration.Branch',db_column="branch", null=True, blank=True, on_delete=models.CASCADE)
    POSTERMINAL = models.ForeignKey('configuration.POSTerminal',db_column="terminal", null=True, blank=True, on_delete=models.CASCADE)
    COMPANY = models.ForeignKey('configuration.Company',db_column="company", null=True, blank=True, on_delete=models.CASCADE)

    DEPT = models.CharField(db_column="dept", max_length=25, null=True, blank=True)

    def save(self):

        for field in self._meta.fields:
            if isinstance(field, (CharField, TextField)):
                if getattr(self, field.attname) is None or getattr(self, field.attname) == '':
                    setattr(self, field.attname, " ")
            if isinstance(field, (IntegerField, FloatField)):
                if getattr(self, field.attname) is None or getattr(self, field.attname) == '':
                    setattr(self, field.attname, 0)
            if isinstance(field, (DateField ,DateTimeField)):
                if getattr(self, field.attname) is None or getattr(self, field.attname) == '':
                    setattr(self, field.attname, '1900-01-01')    
        super().save()
        
    # class Meta:
    #     db_table = "gledg"
    #     # managed = False 

    #     indexes = [
    #     models.Index(fields=["V_TYPE", "VNO"]),
    #     models.Index(fields=["ACC_CODE"]),
    #     models.Index(fields=["DATE"]),
    #     models.Index(fields=["AMT_TYPE"]),
    # ]

    class Meta:
        db_table = "gledg"

        indexes = [
            models.Index(
                fields=["DATE", "DATEENT", "GLEDG_ID"],
                name="gledg_daybook_idx"
            ),

            models.Index(
                fields=["V_TYPE", "VNO"],
                name="gledg_vtype_vno_idx"
            ),

            models.Index(
                fields=["ACC_CODE"],
                name="gledg_acc_code_idx"
            ),

            models.Index(
                fields=["AMT_TYPE"],
                name="gledg_amt_type_idx"
            ),
        ]


    def __str__(self):
        return f"{self.GLEDG_ID} - {self.ACC_CODE}"









class Vchno(models.Model):
    id = models.AutoField(db_column="id", primary_key=True)

    TYPE = models.CharField(
        db_column="type",
        max_length=6,
        unique=True,
    )

    VCHNO = models.IntegerField(
        db_column="vchno",
        default=0
    )

    REMARKS = models.CharField(
        db_column="remarks",
        max_length=50,
        blank=True,
        null=True
    )

    JAN = models.IntegerField(db_column="jan", default=0)
    FEB = models.IntegerField(db_column="feb", default=0)
    MAR = models.IntegerField(db_column="mar", default=0)
    APR = models.IntegerField(db_column="apr", default=0)
    MAY = models.IntegerField(db_column="may", default=0)
    JUN = models.IntegerField(db_column="jun", default=0)
    JUL = models.IntegerField(db_column="jul", default=0)
    AUG = models.IntegerField(db_column="aug", default=0)
    SEP = models.IntegerField(db_column="sep", default=0)
    OCT = models.IntegerField(db_column="oct", default=0)
    NOV = models.IntegerField(db_column="nov", default=0)
    DECE = models.IntegerField(db_column="dece", default=0)

    class Meta:
        db_table = "vchno"
        # managed = True

    def __str__(self):
        return f"{self.TYPE} - {self.REMARKS}"