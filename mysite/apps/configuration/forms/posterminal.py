# from apps.configuration.models import POSTerminal
# from django import forms


from django import forms
from apps.configuration.models import POSTerminal


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Select the first company by default
        if not self.instance.pk:
            if self.fields['company'].queryset.exists():
                self.fields['company'].initial = (
                    self.fields['company'].queryset.first().pk
                )

            # Select the first branch by default
            # if self.fields['branch'].queryset.exists():
            #     self.fields['branch'].initial = (
            #         self.fields['branch'].queryset.first().pk
            #     )

        # Remove the empty "---------" option
        self.fields['company'].empty_label = None
        # self.fields['branch'].empty_label = None
        
        
        
# class POSTerminalForm(forms.ModelForm):
#     class Meta:
#         model = POSTerminal
#         fields = '__all__'
#         widgets = {
#             'name': forms.TextInput(attrs={
#                 'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-transparent text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition', 
#                 'placeholder': 'Terminal Name'
#             }),
#             'company': forms.Select(attrs={
#                 'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-[var(--bg-surface)] text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'
#             }),
#             'branch': forms.Select(attrs={
#                 'class': 'w-full border border-[var(--border-color)] rounded-lg px-3 py-2 bg-[var(--bg-surface)] text-sm text-[var(--text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition'
#             }),
#             'is_active': forms.CheckboxInput(attrs={
#                 'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 transition'
#             }),
#         }
        
        
        
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         # Select the first company by default
#         if not self.instance.pk:
#             if self.fields['company'].queryset.exists():
#             self.fields['company'].initial = (
#                 self.fields['company'].queryset.first().pk
#             )

#         # Select the first branch by default
#         if self.fields['branch'].queryset.exists():
#             self.fields['branch'].initial = (
#                 self.fields['branch'].queryset.first().pk
#             )

#         # Remove the empty "---------" option
#         self.fields['company'].empty_label = None
#         self.fields['branch'].empty_label = None

