/* ══════════════════════════════════════════════════════
   Inventory Search Config — GlobalSearchModal
   ──────────────────────────────────────────────────────
   Customize: displayColumns, searchFields, excludeFilters,
   onSelect callback, triggerSelector, hotkey, etc.
   ══════════════════════════════════════════════════════ */
// const InventoryHelpers = new InventoryHelpers()

import InvHelpers from '/static/inventory/js/services/inventory_helpers.js'
import {GlobalSearchModal} from '/static/mysearch/js/global_search_modal.js'

GlobalSearchModal.init([
    // {
    //     modalId: 'inventorySearch',
    //     triggerSelector: '#viewListBtn', // Opens when this button is clicked
    //     triggerKey: 'F3',                       // Opens when this key is pressed
    //     triggerInputId: 'id_prod_name',         // ONLY opens if F3 is pressed while THIS input is focused (optional)

    //     title: 'Find Product',
    //     placeholder: 'Search by name, barcode, ID...',

    //     appLabel: 'inventory',
    //     modelName: 'Inventory',
    //     primaryKey: 'inv_id',

    //     // IndexedDB store name (null = always use server)
    //     indexdbStore: 'inventory',

    //     // Fields to search against (local fuzzy + server icontains)
    //     searchFields: ['prod_name', 'alias_name', 'barcode', 'manualbc', 'inv_id'],

    //     // Columns shown in results table
    //     displayColumns: [
    //         { key: 'inv_id',     header: 'ID',           width: '70px' },
    //         { key: 'prod_name',  header: 'Product Name'                },
    //         { key: 'barcode',    header: 'Barcode',      width: '140px' },
    //         { key: 'base_price', header: 'Price',        width: '100px' },
    //     ],

    //     // Exclude items matching these from local results
    //     excludeFilters: { active: false },

    //     pageSize: 50,

    //     // Called when user selects an item (Enter / double-click)
    //     onSelect: function (item) {
    //         console.log('Inventory item selected:', item);
    //         InvHelpers.fetchAndFillInventoryData(item.inv_id)
            
    //         // Example: fill form fields
    //         // document.getElementById('id_prod_name').value = item.prod_name;
    //     }
    // },

    {
        modalId: 'select-account',
        triggerSelector: '#btn-select-account',
        triggerKey: 'F3',                    // optional hotkey
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
            document.getElementById('globalAccCode').value = item.ACC_CODE;
            document.getElementById('applyCodeToRows').click();
        }
    },


]);

