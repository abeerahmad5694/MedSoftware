import InvHelpers from '/static/inventory/js/services/inventory_helpers.js';
import { InlineSearchWidget } from '/static/inventory/js/services/inline_search_widget.js';

document.addEventListener('keydown', function(e) {
    if (e.key === 'F2') {
        e.preventDefault();
        const form = document.getElementById('inventoryForm');
        if (form) {
            form.requestSubmit();
        }
    }
});



document.getElementById('delete_inventory_item').addEventListener('click', function(e) {
    e.preventDefault();
    InvHelpers.deleteInventoryItem();
    console.log('delete_inventory_item clicked')
});

document.getElementById('copySameItemBtn').addEventListener('click', function(e) {
    e.preventDefault();
    InvHelpers.copySameItem();
    console.log('copySameItemBtn clicked')
});

document.addEventListener('DOMContentLoaded', async function() {


    IndexDBConfig.sync_indexdb('inventory', 'Inventory');

    const form = document.getElementById('inventoryForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            InvHelpers.saveUpdateInventory();
        });
    }

    if(!window.companyConfigurations){
        // console.log('This si running')
        await window.loadCompanyConfigurations();
    }



    // Inline Quick Find widget — reuses GlobalSearchModal search engine
    window._iswInventory = new InlineSearchWidget({
        containerId: 'iswContainer',
        inputId: 'iswSearchInput',
        resultsId: 'iswResults',
        countId: 'iswCount',

        indexdbStore: 'inventory',
        primaryKey: 'inv_id',
        searchFields: ['prod_name', 'alias_name', 'barcode', 'manualbc', 'inv_id'],
        displayColumns: [
            { key: 'inv_id',    header: 'ID',   width: '50px' },

            // { key: 'prod_picture_thumb', header: 'Img', width: '40px', render: (val, item) => {
            //     if (val && window.companyConfigurations?.inventory?.pictures_allowed === true) return `<img src="/media/${val}" class="w-8 h-8 object-cover rounded shadow-sm border border-gray-200" style="min-width:32px;">`;
            //     else if (val == null && window.companyConfigurations?.inventory?.pictures_allowed === true) return `<img src="/static/no-image.webp" class="w-8 h-8 object-cover rounded shadow-sm border border-gray-200 opacity-50" style="min-width:32px;">`;
            //     else return '';
            // }},
            ...(window.companyConfigurations?.inventory?.pictures_allowed === true
            ? [{
                key: 'prod_picture_thumb',
                header: 'Img',
                width: '40px',
                render: (val, item) => {
                    if (val) {
                        return `<img src="/media/${val}" class="w-8 h-8 object-cover rounded shadow-sm border border-gray-200" style="min-width:32px;">`;
                    }

                    return `<img src="/static/no-image.webp" class="w-8 h-8 object-cover rounded shadow-sm border border-gray-200 opacity-50" style="min-width:32px;">`;
                }
            }]
            : []),
            { key: 'prod_name', header: 'Name' },
            { key: 'base_price',header: 'Price', width: '70px' },
        ],
        excludeFilters: { active: false },
        pageSize: 15,

        onSelect: function (item) {
            InvHelpers.fetchAndFillInventoryData(item.inv_id);
        }
    });

    
    // console.log('This si running')
    if(window.companyConfigurations?.inventory?.pictures_allowed === true){
        // console.log('This si running')
        document.getElementById('image-section').classList.remove('hidden');
    } else {
        const identityCard = document.querySelector('.identity-card');
        identityCard.style.gridTemplateColumns = '1fr';
    }


    if(window.companyConfigurations?.inventory?.dzn_pack_name && window.companyConfigurations?.inventory?.dzn_pack_name != ''){
        // console.log('This si running')
        document.getElementById('dzn_pack_box').classList.remove('hidden');
        document.getElementById('dzn_pack_label').innerText = `${window.companyConfigurations?.inventory?.dzn_pack_name || 'Dozen'}`;
    }
    if(window.companyConfigurations?.inventory?.carton_pack_name && window.companyConfigurations?.inventory?.carton_pack_name != ''){
        // console.log('This si running')
        document.getElementById('carton_pack_box').classList.remove('hidden');
        document.getElementById('carton_pack_label').innerText = window.companyConfigurations?.inventory?.carton_pack_name || 'Carton';
    }
    // console.log(window.companyConfigurations?.inventory?.allow_stock_variation)
    // console.log(typeof(window.companyConfigurations?.inventory?.allow_stock_variation))

    const allowVariation =
    window.companyConfigurations?.inventory?.allow_stock_variation;

    const variationGroup = document.getElementById('variation-type-group');

    console.log('This is variation logic..',{
        allowVariation,
        type: typeof allowVariation,
        variationGroup
    });



    if (window.companyConfigurations?.inventory?.allow_stock_variation) {
        if (variationGroup) {
            variationGroup.classList.remove('hidden');
        }
    }




    //const form = document.getElementById('inventoryForm');

    if (!form) return;

    form.addEventListener('keydown', function (e) {

        if (e.key !== 'Enter') return;

        // Allow Enter inside textareas
        if (e.target.tagName === 'TEXTAREA') return;

        // Prevent form submission
        e.preventDefault();

        // Get all visible, enabled form fields
        const fields = Array.from(form.querySelectorAll(
            'input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="file"]), select, textarea, button'
        )).filter(field =>
            !field.disabled &&
            field.offsetParent !== null &&
            field.type !== 'button'
        );

        const currentIndex = fields.indexOf(e.target);

        if (currentIndex !== -1) {

            // Move to next field
            const nextField = fields[currentIndex + 1];

            if (nextField) {
                nextField.focus();

                // Select text in input fields
                if (nextField.tagName === 'INPUT' &&
                    ['text', 'number', 'search'].includes(nextField.type)) {
                    nextField.select();
                }
            }
        }
    });





    





});
