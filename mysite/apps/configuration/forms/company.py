from apps.configuration.models import Company
from django import forms

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Company Name'}),
            'name_ur': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'کمپنی کا نام', 'dir': 'rtl', 'lang': 'ur', 'style': 'font-family: "Jameel Noori Nastaleeq", serif;'}),
            'address': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Main Address'}),
            'address_ur': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'کمپنی کا پتہ', 'dir': 'rtl', 'lang': 'ur', 'style': 'font-family: "Jameel Noori Nastaleeq", serif;'}),
            'phone1': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Primary Phone'}),
            'phone2': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Secondary Phone'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Email Address'}),
            'license_no': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'License Number'}),
            'ntn_no': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'NTN Number'}),
            'ntn_no_ur': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'NTN نمبر', 'dir': 'rtl', 'lang': 'ur', 'style': 'font-family: "Jameel Noori Nastaleeq", serif;'}),
            'logo': forms.FileInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'}),
        }