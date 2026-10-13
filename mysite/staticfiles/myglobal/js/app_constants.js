
// This is just a fallback, the real value is set by Django

class ContantApi {
    constructor() {
        this.myglobal_app = 'myglobal';
        this.global_inline_modal_lookup_api = `${this.myglobal_app}/lookup`;
        this.fetch_full_model_api = `${this.myglobal_app}/fetch_full_model`;
        this.sync_indexdb_api = `${this.myglobal_app}/sync_indexdb`;

        this.mysearch_app = 'mysearch';
        this.global_search_api = `${this.mysearch_app}/search`;

        this.inventory_app = 'inventory';
        this.get_inventory_item_by_id = `${this.inventory_app}/get_item_by_id`;
        this.save_update_inventory = `${this.inventory_app}/api/save_update_inventory`;
        this.delete_inventory_item = `${this.inventory_app}/api/delete_inventory_item`;

        this.sale_app = 'sale';
        this.save_sale_bills_api = `/${this.sale_app}/api/save_bills/`;
        this.get_sale_bill_api = `/${this.sale_app}/api/get_bill/`
        this.sale_add_cart_api = `/${this.sale_app}/api/add_cart/`;

        this.purchase_app = 'purchase'
        this.save_purchase_bills_api = `/${this.purchase_app}/api/save_bills/`;
        this.get_purchase_bill_api = `/${this.purchase_app}/api/get_bill/`
        // this.purchase_add_cart_api = `/${this.purchase_app}/api/add_cart/`;

        this.quotation_app = 'quotation';
        this.save_quotation_bills_api = `/${this.quotation_app}/api/save_bills/`;
        this.get_quotation_bill_api = `/${this.quotation_app}/api/get_bill/`
        



        this.myledger_app = 'myledger'
        this.get_all_banks_api = `/${this.myledger_app}/api/get_banks`;





    }
}

window.app_constants = new ContantApi();
