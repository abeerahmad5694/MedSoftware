from django import forms
from apps.inventory.models import Inventory

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = "__all__"
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        
        # company = kwargs.pop('company', None)
        # branch = kwargs.pop('branch', None)
        super().__init__(*args, **kwargs)
        # if company:
        #     self.fields['company'].initial = company
        # if branch:
        #     self.fields['branch'].initial = branch
        for field_name, field in self.fields.items():
            # Set required=False for fields that allow null in the model
            try:
                model_field = Inventory._meta.get_field(field_name)
                if model_field.null:
                    field.required = False
            except:
                pass
            active = forms.BooleanField(initial=True, required=False)
            # Basic styling for all fields
            field.widget.attrs.update({
                'class': 'erp-input-field h-7 text-xs border border-[var(--border-color)] rounded px-2 bg-white text-[var(--text-main)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] transition w-full',
                'placeholder': field_name.replace('_', ' ').title()
            })
            
            # Specific styling for select fields
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'erp-input-field h-7 text-xs border border-[var(--border-color)] rounded px-1 bg-white text-[var(--text-main)] focus:outline-none w-full'
                })

            # Specific styling for checkboxes
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'w-4 h-4 rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)]'
                })
            
            # Special case for product name (big field)
            if field_name == 'prod_name':
                field.widget.attrs.update({
                    'class': 'big-name-field h-10 text-lg font-bold border-2 border-black rounded px-3 bg-black text-white focus:outline-none w-full',
                    'placeholder': 'ENTER PRODUCT NAME...'
                })
            
            if field_name == 'prod_name_ur':
                field.widget.attrs.update({
                    'class': 'big-name-field h-10 text-lg font-bold border-2 border-black rounded px-3 bg-gray-800 text-white focus:outline-none w-full',
                    'placeholder': 'آئٹم کا نام درج کریں...',
                    'dir': 'rtl',
                    'lang': 'ur',
                    'style': 'font-family: "Jameel Noori Nastaleeq", serif; text-align: right;'
                })



            if field_name == 'prod_picture':
                field.widget = forms.FileInput(attrs={
                    'accept': 'image/*',
                    'class': 'hidden',
                    'id': 'product-image-input'
                })
        # self.fields['company'].widget.attrs.update({'hidden': True})
        # self.fields['branch'].widget.attrs.update({'hidden': True})
        # self.fields['company'].initial = company
        # self.fields['branch'].initial = branch
        # self.fields['company'].initial = kwargs.get('company')
        # self.fields['branch'].initial = kwargs.get('branch')

        # self.fields['brand'].required = False   
        self.fields['brand'].empty_label = 'Enter Manufacturer Name...'
        self.fields['brand'].widget.attrs.pop('required', None)