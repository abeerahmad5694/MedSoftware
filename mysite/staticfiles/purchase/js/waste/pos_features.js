
const urlforfeatures = '/sale/Pos_features/'
let features = {
    pos_discount_per_item:false,
    pos_load_prv_bill:false,
    pos_disc_flat_limit:100,
}
let barcode_config ={
    price_base:'Normal',
    total_bc_digits:13,
    left_delete:2,
    right_delete:1,
    item_bc:5,
    kg:2,
    grm:3,
}



async function get_features(){
    return fetch(urlforfeatures)
        .then(res=>res.json())
        .then((data)=>{
            Object.assign(features,data.features)
            Object.assign(barcode_config,data.barcode_config)
        })
}



export {features,get_features,barcode_config}