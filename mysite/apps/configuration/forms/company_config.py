from django import forms
from apps.configuration.models import CompanyConfiguration, Company, Branch

class CompanyConfigurationForm(forms.ModelForm):
    all_branches = forms.BooleanField(required=False, label="Apply to All Branches")

    class Meta:
        model = CompanyConfiguration
        # fields = ['company', 'branch', 'promotion_disc_percent_bill', 'promotion_disc_percent_item', 
        #           'multiple_bill_prints', 'pos_sale_receipt_size', 'credit_sale_receipt_size', 'purchase_receipt_size']
        
        fields= '__all__'
        widgets = {
            'company': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
            'branch': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
            'promotion_disc_percent_bill': forms.NumberInput(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
                'placeholder': 'Disc %'
            }),
            'promotion_disc_percent_item': forms.NumberInput(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
                'placeholder': 'Disc %'
            }),
            'multiple_bill_prints': forms.NumberInput(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
                'placeholder': 'No. of Prints'
            }),
            'pos_sale_receipt_size': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
            'credit_sale_receipt_size': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
            'purchase_receipt_size': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
            'stock_valuation_method': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_superuser:
            # For regular users, make company and branch read-only
            self.fields['company'].disabled = True
            self.fields['branch'].disabled = True
            # We can also strip the arrow from select for cleaner look if needed, 
            # but disabled already communicates "read-only"
        
        if user and user.is_superuser:
            # Superuser might want to see all or specific branches.
            # For now, keep as is, but we could restrict branches if a company is selected.
            pass
