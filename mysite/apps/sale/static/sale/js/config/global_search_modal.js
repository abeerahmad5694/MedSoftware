

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
        // indexdbStore: null,
        indexdbStore: 'inventory',
        
        // Fields to search against (local fuzzy + server icontains)
        searchFields: ['prod_name', , 'serial_no','alias_name', 'barcode', 'manualbc', 'inv_id'],

        pipelines: [
            {
                id: 'numeric',
                condition: (q) => /^\d+$/.test(q),
                rules: [
                    { if: (q) => q.length <= 6, field: 'inv_id',    lookup: 'exact', rank: 100, stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'barcode',   lookup: 'exact', rank: 100, stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'barcode2',  lookup: 'exact', rank: 95,  stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'manualbc',  lookup: 'exact', rank: 90,  stop_if_found: true },
                    // { if: (q) => q.length >= 5, field: 'serial_no',  lookup: 'exact', rank: 90,  stop_if_found: true },
                    { field: 'serial_no', lookup: 'exact', rank: 100, stop_if_found: true },
                ]
            },
            {
                id: 'string',
                condition: (q) => true,
                rules: [
                    { field: 'serial_no',  lookup: 'exact',     rank: 110, stop_if_found: true },
                    { field: 'serial_no',  lookup: 'token_and', rank: 85 },
                    { field: 'manualbc',   lookup: 'exact',     rank: 100, stop_if_found: true },
                    { field: 'barcode2',   lookup: 'exact',     rank: 90,  stop_if_found: true },
                    { field: 'alias_name', lookup: 'exact',     rank: 80,  stop_if_found: true },
                    { field: 'barcode',    lookup: 'exact',     rank: 70,  stop_if_found: true },
                    { field: 'prod_name',  lookup: 'token_and', rank: 50 },
                    { field: 'alias_name', lookup: 'token_and', rank: 40 },
                ]
            }
        ],

        

        // Columns shown in results table
        displayColumns: [
            { key: 'inv_id',     header: 'ID',           width: '70px' },
            { key: 'prod_name',  header: 'Product Name'                },
            { key: 'serial_no',  header: 'Serial No',    width: '140px' },
            { key: 'ram',        header: 'RAM',    width: '140px' },
            { key: 'storage',    header: 'Storage',    width: '140px' },
            { key: 'base_price', header: 'Price',        width: '100px' },
            // { key: 'barcode',    header: 'Barcode',      width: '140px' },
        ],

        // Exclude items matching these from local results
        excludeFilters: { active: false, tracking_type: "SERIAL" },

        pageSize: 14,

        // Called when user selects an item (Enter / double-click)
        onSelect: function (item) {
            // console.log(item)
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



    



    

    