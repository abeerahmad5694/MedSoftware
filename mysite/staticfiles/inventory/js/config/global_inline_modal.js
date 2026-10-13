

import GlobalInlineModal from '/static/myglobal/js/services/global_inline_modal.js'

GlobalInlineModal.init([
        {
            buttonSelector: '#addBrandBtn',
            targetSelectSelector: '#id_brand',
            appLabel: 'inventory',
            modelName: 'ItemBrand',
            label: 'Brand'
        },
        {
            buttonSelector: '#addCompanyBtn',
            targetSelectSelector: '#id_manufacturer',
            appLabel: 'inventory',
            modelName: 'ItemCompany',
            label: 'Company'  
        },
        {
            buttonSelector: '#addCategoryBtn',
            targetSelectSelector: '#id_category',
            appLabel: 'inventory',
            modelName: 'ItemCategory',
            label: 'Category'
        },
        {
            buttonSelector: '#addSubCategoryBtn',
            targetSelectSelector: '#id_subcategory',
            appLabel: 'inventory',
            modelName: 'ItemSubCategory',
            label: 'Sub-Category'
        },
        {
            buttonSelector: '#addBaseUnitBtn',
            targetSelectSelector: '#id_base_uom',
            appLabel: 'inventory',
            modelName: 'Unit',
            label: 'Base Unit'
        },
        {
            buttonSelector: '#addCartonUnitBtn',
            targetSelectSelector: '#id_carton_uom',
            appLabel: 'inventory',
            modelName: 'Unit',
            label: 'Carton Unit'
        },
        {
            buttonSelector: '#addDznUnitBtn',
            targetSelectSelector: '#id_dzn_uom',
            appLabel: 'inventory',
            modelName: 'Unit',
            label: 'Dozen Unit'
        }
    ]);