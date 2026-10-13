def dynamic_js_urls(request):
    return {
        'global_inline_modal_js': 'myglobal/js/services/global_inline_modal.js',
        'app_constants_js': 'myglobal/js/app_constants.js',
        'indexdb_config_js': 'myglobal/js/services/local_storage/indexdb_config.js',
        'fetch_full_model_js': 'myglobal/js/apis/fetch_full_model.js',
        'main_js': 'js/main.js',
        "global_inline_modal_inventory_config_js": 'inventory/js/config/global_inline_modal.js',
        'global_search_modal_js': 'mysearch/js/global_search_modal.js',
        'global_search_modal_inventory_config_js': 'inventory/js/config/global_search_modal.js',
        'inventory_helpers_js': 'inventory/js/services/inventory_helpers.js',
        'inventory_js': 'inventory/js/inventory.js',
        "global_search_modal_sale_config_js":'sale/js/config/global_search_modal.js',




        # # purchase row cart fields map to diplay in cart and save 
        # 'purchase_cart_field_map':{
        #     {'heading':'ID','field':'inv_id','field_type':'number'},
        #     {'heading':'Item Name','field':'prod_name','field_type':'text'},
        #     {'heading':'Lot/BatchNo','field':'row_batch_no','field_type':'text'},
        #     {'heading':'Qty','field':'qty','field_type':'number'},
        #     {'heading':'Packing Mode','field':'packing_mode','field_type':'select'},            
        #     {'heading':'Pack Qty','field':'pack_qty','field_type':'number'},
        #     {'heading':'Discount %','field':'discount_percent_per_item'},
        #     {'heading':'Discount Amount','field':'discount'},
        #     {'heading':'Net Total','field':'row_net_total'},
        #     {'heading':'Row Notes','field':'row_notes'},
        #     {'heading':'Expiry Date','field':'row_expiry_dt'},
        # }
    }