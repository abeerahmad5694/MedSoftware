from django import forms
from .models import Accounts


class AccountsForm(forms.ModelForm):
    
    class Meta:
        model = Accounts

        fields = [
            "ACC_CODE",
            "ACC_NAME",
            "ADDRESS",
            "CITY",
            "COUNTRY",
            "MOBILE_NO",
            "PHONE_OFF",
            "EMAIL_ADDRESS",
            "OPENING_BALANCE",
            "BALANCE_TYPE",
            "CREDIT_LIMIT",
            "REMARKS",
            "NTN_NO",
            "STN_NO",
            "SALESMAN",
            # 'LOCKED',
            "PASSWORD",
        ]

        widgets = {
            "ACC_CODE": forms.NumberInput(attrs={"class": "account-form-input"}),
            "ACC_NAME": forms.TextInput(attrs={"class": "account-form-input"}),
            "ADDRESS": forms.TextInput(attrs={"class": "account-form-input"}),
            "CITY": forms.TextInput(attrs={"class": "account-form-input"}),
            "COUNTRY": forms.TextInput(attrs={"class": "account-form-input"}),
            "MOBILE_NO": forms.TextInput(attrs={"class": "account-form-input"}),
            "PHONE_OFF": forms.TextInput(attrs={"class": "account-form-input"}),
            "EMAIL_ADDRESS": forms.EmailInput(attrs={"class": "account-form-input"}),
            "OPENING_BALANCE": forms.NumberInput(attrs={"class": "account-form-input"}),
            "BALANCE_TYPE": forms.TextInput(attrs={"class": "account-form-input"}),
            "CREDIT_LIMIT": forms.NumberInput(attrs={"class": "account-form-input"}),
            "REMARKS": forms.Textarea(attrs={"class": "account-form-input"}),
            "NTN_NO": forms.TextInput(attrs={"class": "account-form-input"}),
            "STN_NO": forms.TextInput(attrs={"class": "account-form-input"}),
            "SALESMAN": forms.TextInput(attrs={"class": "account-form-input"}),
            # 'LOCKED':forms.CheckboxInput(attrs={'class':'account-from-input'}),
            "PASSWORD": forms.PasswordInput(attrs={"class": "account-form-input"}),
        }