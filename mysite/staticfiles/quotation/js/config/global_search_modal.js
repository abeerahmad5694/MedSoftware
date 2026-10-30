

import {GlobalSearchModal} from '/static/mysearch/js/global_search_modal.js'
import { addToLocalCart, renderCart } from "../cart.js";


GlobalSearchModal.init([
    {
        modalId: 'inventorySearch',
        triggerSelector: '#btn-search', // Opens when this button is clicked
        triggerKey: 'F3',                       // Opens when this key is pressed
        triggerInputId: 'product-search',         // ONLY opens if F3 is pressed while THIS input is focused (optional)

        title: 'Find Product',
        placeholder: 'Search by name, barcode, ID...',

        appLabel: 'inventory',
        modelName: 'Inventory',
        primaryKey: 'inv_id',

        // IndexedDB store name (null = always use server)
        indexdbStore: 'inventory',

        // Fields to search against (local fuzzy + server icontains)
        searchFields: ['prod_name', 'alias_name', 'barcode', 'manualbc', 'inv_id'],

        // Columns shown in results table
        displayColumns: [
            { key: 'inv_id',     header: 'ID',           width: '70px' },
            { key: 'prod_name',  header: 'Product Name'                },
            { key: 'barcode',    header: 'Barcode',      width: '140px' },
            { key: 'base_price', header: 'Price',        width: '100px' },
        ],

        // Exclude items matching these from local results
        excludeFilters: { active: false },

        pageSize: 14,

        // Called when user selects an item (Enter / double-click)
        onSelect: function (item) {
            console.log(item)
            // console.log('Inventory item selected:', item);
            document.getElementById('product-search').focus();
            const cart = addToLocalCart(item);
            renderCart(cart);
        }
    } ,
    
    

// config for select account
    {
        modalId: 'select-client',
        triggerSelector: '#btn-select-client',
        triggerKey: 'ctrl+c',                    // optional hotkey
        title: 'Find Account',
        placeholder: 'Search by account head, name, code ...',
        appLabel: 'myaccounts',
        modelName: 'Accounts',
        primaryKey: 'ACC_CODE',
        indexdbStore: null,            // null = skip local
        searchFields: ['ACC_CODE', 'ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '80px' },
            { key: 'ACC_NAME', header: 'Account Name' },
        ],
        excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
        pageSize: 10,
        onSelect: async (item) => {
            document.getElementById('acc_code').value = item.ACC_CODE;
            document.getElementById('last-bill-amount').innerHTML = 'Client: ' + item.ACC_NAME
            document.getElementById('product-search').focus();
        }
    },
]);





// configs for select account



    



    

    