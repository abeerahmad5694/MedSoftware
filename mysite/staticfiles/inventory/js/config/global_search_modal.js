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
    {
        modalId: 'inventorySearch',
        triggerSelector: '#viewListBtn', // Opens when this button is clicked
        triggerKey: 'F3',                       // Opens when this key is pressed
        triggerInputId: 'id_prod_name',         // ONLY opens if F3 is pressed while THIS input is focused (optional)

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
            console.log('Inventory item selected:', item);
            InvHelpers.fetchAndFillInventoryData(item.inv_id)
            
            // Example: fill form fields
            // document.getElementById('id_prod_name').value = item.prod_name;
        }
    }
]);

