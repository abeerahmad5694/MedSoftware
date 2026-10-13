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

document.addEventListener('DOMContentLoaded', function () {
    IndexDBConfig.sync_indexdb('inventory', 'Inventory');

    const form = document.getElementById('inventoryForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            InvHelpers.saveUpdateInventory();
        });
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
            { key: 'prod_name', header: 'Name' },
            { key: 'base_price',header: 'Price', width: '70px' },
        ],
        excludeFilters: { active: false },
        pageSize: 15,

        onSelect: function (item) {
            InvHelpers.fetchAndFillInventoryData(item.inv_id);
        }
    });
});
