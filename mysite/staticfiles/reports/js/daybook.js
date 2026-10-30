// import { ReceiptModal } from "/static/common/js/recept_modal.js";
// import { fetchBill } from "/static/common/js/fetch_old_bill.js";
// import { features,get_features } from "/static/common/js/pos_features.js";
// import JournalVoucherModal from '/static/accounts/js/jv_pro_modal.js'





const table = document.querySelector('table')
const edit_selected_row = document.getElementById('edit_selected_row')
const preview_selected_row = document.getElementById('preview_selected_row')
let selected_row_id = null
let activerow = null

import { openDynamicVoucherModal } from "/static/myledger/js/modals/dynamic_voucher_modal.js";
import { openAccountModal } from "/static/myaccounts/js/modals/global_account_form_modal.js";
import { openJvVoucherModal } from "/static/myledger/js/modals/jv_voucher_modal.js";





    
document.addEventListener('click',(e)=>{
    const validVtype=['CR','CP','BR','BP','JV','INV','PUR'];
    
    const cell = e.target.closest('.ledgerRowCell')
    if(!cell) return;
    // console.log('cell',cell)

    const cellValue = cell.textContent.trim();
    const cellName = cell.dataset.key;
    const v_typeCell  = cell.previousElementSibling;
    const v_typeValue = v_typeCell?.textContent.trim();

    
    if((cellName !=='vno' && cellName!== 'acc_code')|| cellValue=="") return;
    if (cellName=='acc_code'){
        if (!cellValue || cellValue == 0) return alert('Please enter account code');
        openAccountModal(parseInt(cellValue), 4);
    }else if ((cellName=='vno' && validVtype.includes(v_typeValue))){

        console.log('v_typevalue = ',v_typeValue)
        if(v_typeValue=='PUR' || v_typeValue == 'INV') {
            if(v_typeValue=='PUR'){
                window.open(`/purchase/?bill_no=${cellValue}`)
            }
            if(v_typeValue=='INV'){
                window.open(`/sale/?bill_no=${cellValue}`)
            }
            return
        }
        v_typeValue != 'JV' ? openDynamicVoucherModal(v_typeValue, cellValue) : openJvVoucherModal(cellValue);
    }

})


// document.addEventListener('DOMContentLoaded',async ()=>{    
//     await get_features()
    
//     if(table){

    
//     table.addEventListener('click',(e)=>{
//         let row = e.target.closest('.table_row')
//         if (activerow) {
//             activerow.classList.remove('selected')}

//         row.classList.add("selected")
//         activerow = row
//         selected_row_id = row.dataset.id

//     })

//     if(features.pos_load_prv_bill){
//     edit_selected_row.addEventListener('click',()=>{
//         if(activerow && selected_row_id){
//             window.open(`/sale/?voucher_no=${selected_row_id}`)

//         }
//         else{
//             alert('NO ITEM SELECTED')
//         }
//     })}

//     preview_selected_row.addEventListener('click',()=>{
//         if(activerow && selected_row_id){
//             fetchBill(selected_row_id)

//         }
//         else{
//             alert('NO ITEM SELECTED')
//         }
//     })}


    
// })

