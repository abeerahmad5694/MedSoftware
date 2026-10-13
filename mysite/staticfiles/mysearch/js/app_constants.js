
// This is just a fallback, the real value is set by Django

export class ContantApi{
    constructor(){
        this.myglobal_app = 'myglobal';
        this.global_inline_modal_lookup_api = `${this.myglobal_app}/lookup`;
        this.fetch_full_model_api = `${this.myglobal_app}/fetch_full_model`;
        this.sync_indexdb_api = `${this.myglobal_app}/sync_indexdb`;

        this.mysearch_app= 'mysearch';
        this.global_search_api = `${this.mysearch_app}/search`;

        this.inventory_app = 'inventory';
        this.get_inventory_item_by_id = `${this.inventory_app}/get_item_by_id`;

        
    }
}

window.app_constants = new ContantApi();
