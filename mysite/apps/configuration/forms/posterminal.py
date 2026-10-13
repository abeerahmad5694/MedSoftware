from apps.configuration.models import POSTerminal
from django import forms

class POSTerminalForm(forms.ModelForm):
    class Meta:
        model = POSTerminal
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 
                'placeholder': 'Terminal Name'
            }),
            'company': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-[var(--bg-surface)] text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'
            }),
            'branch': forms.Select(attrs={
                'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-[var(--bg-surface)] text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 transition'
            }),
        }
