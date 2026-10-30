import {GlobalSearchModal} from '/static/mysearch/js/global_search_modal.js'

GlobalSearchModal.init([
    {
        modalId: 'itemSearch',
        triggerSelector: '#item-search-btn', // Opens when this button is clicked
        triggerKey: 'F3',                       // Opens when this key is pressed
        triggerInputId: 'item_name',         // ONLY opens if F3 is pressed while THIS input is focused (optional)

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
            // Set the hidden input or text input to the item ID
            document.getElementById('inv_id').value = item.inv_id;
            
            // Auto submit the form to load the ledger
            document.getElementById('ledgerForm').submit();
        }
    } ,
])



document.addEventListener('DOMContentLoaded',function(){
    document.getElementById('item_name')?.focus();
})