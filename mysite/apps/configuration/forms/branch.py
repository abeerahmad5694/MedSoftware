from apps.configuration.models import Branch
from django import forms

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Branch Name'}),
            'name_ur': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'برانچ کا نام', 'dir': 'rtl', 'lang': 'ur', 'style': 'font-family: "Jameel Noori Nastaleeq", serif;'}),
            'company': forms.Select(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-[var(--bg-surface)] text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'}),
            'address': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Branch Address'}),
            'address_ur': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'برانچ کا پتہ', 'dir': 'rtl', 'lang': 'ur', 'style': 'font-family: "Jameel Noori Nastaleeq", serif;'}),
            'phone1': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Primary Phone'}),
            'phone2': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Secondary Phone'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'Email Address'}),
            'license_no': forms.TextInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 'placeholder': 'License Number'}),
            'logo': forms.FileInput(attrs={'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'}),
        }
