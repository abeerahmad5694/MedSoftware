

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

        pageSize: 50,

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
        modalId: 'select-account',
        triggerSelector: '#search-account-btn',
        triggerKey: 'ctrl+c',                    // optional hotkey
        title: 'Find Account',
        placeholder: 'Search by account head, name, code ...',
        appLabel: 'myaccounts',
        modelName: 'Accounts',
        primaryKey: 'ACC_CODE',
        indexdbStore: null,            // null = skip local
        searchFields: ['ACC_CODE', 'ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '50px' },
            { key: 'ACC_NAME', header: 'Account Name', width: '800px' },
        ],
        excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
        pageSize: 50,
        onSelect: async (item) => {
            console.log(item)
            document.getElementById('acc_code').value = item.ACC_CODE;
            document.getElementById('supplier-code').value = item.ACC_CODE;
            document.getElementById('supplier-name').value =item.ACC_NAME
            document.getElementById('product-search').focus();
        }
    },


    //for freight account search
    {
        modalId: 'select-freight-account',  
        triggerSelector: '#freight_acc_code_search_btn',
        triggerKey: 'ctrl+f',                    // optional hotkey
        title: 'Find Account',
        placeholder: 'Search by account head, name, code ...',
        appLabel: 'myaccounts',
        modelName: 'Accounts',
        primaryKey: 'ACC_CODE',
        indexdbStore: null,            // null = skip local
        searchFields: ['ACC_CODE', 'ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '200px' },
            { key: 'ACC_NAME', header: 'Account Name', width: '600px' },
        ],
        excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
        pageSize: 50,
        onSelect: async (item) => {
            console.log(item)
            document.getElementById('freight_acc_code').value = item.ACC_CODE;
            document.getElementById('freight_acc_code_desc').value =item.ACC_NAME
            document.getElementById('freight-amt').focus();
        }
    },

    // for labour search
    {
        modalId: 'labour_acc_code',
        triggerSelector: '#labour_acc_code_search_btn',
        triggerKey: 'ctrl+c',                    // optional hotkey
        title: 'Find Account',
        placeholder: 'Search by account head, name, code ...',
        appLabel: 'myaccounts',
        modelName: 'Accounts',
        primaryKey: 'ACC_CODE',
        indexdbStore: null,            // null = skip local
        searchFields: ['ACC_CODE', 'ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '200px' },
            { key: 'ACC_NAME', header: 'Account Name', width: '800px' },
        ],
        excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
        pageSize: 50,
        onSelect: async (item) => {
            console.log(item)
            document.getElementById('labour_acc_code').value = item.ACC_CODE;
            document.getElementById('labour_acc_code_desc').value =item.ACC_NAME
            document.getElementById('labout-amt').focus();
        }
    },
    
    {
        modalId: 'select-unload-account',
        triggerSelector: '#unload_acc_code_search_btn',
        triggerKey: 'ctrl+u',                    // optional hotkey
        title: 'Find Account',
        placeholder: 'Search by account head, name, code ...',
        appLabel: 'myaccounts',
        modelName: 'Accounts',
        primaryKey: 'ACC_CODE',
        indexdbStore: null,            // null = skip local
        searchFields: ['ACC_CODE', 'ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '200px' },
            { key: 'ACC_NAME', header: 'Account Name', width: '800px'},
        ],
        excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
        pageSize: 50,
        onSelect: async (item) => {
            console.log(item)
            document.getElementById('unload_acc_code').value = item.ACC_CODE;
            document.getElementById('unload_acc_code_desc').value =item.ACC_NAME
            document.getElementById('unload-amt').focus();
        }
    },
]);





// configs for select account



    



    

    