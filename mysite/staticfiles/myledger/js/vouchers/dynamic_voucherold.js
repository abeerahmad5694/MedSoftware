
// Get modal elements
const modal = document.getElementById('cashReceiptModal');
const cash_receipt_button = document.getElementById('cash_receipt');
const cash_payment_button = document.getElementById('cash_payment');
const bank_receipt_button = document.getElementById('bank_receipt');
const bank_payment_button = document.getElementById('bank_payment');
const jv_button = document.getElementById('jv_voucher');
const save_voucher_modal_button = document.getElementById('voucher_modal_save_button')
const hidden_voucher_type_value = document.getElementById('hidden_voucher_type_value')
const voucher_modal_total = document.getElementById('voucher_modal_total')
const closeBtn = document.getElementById('closeModal');
const acc_code = document.getElementById('acc_code');
const head = document.getElementById('head');
const voucher_type = document.getElementById('voucher_type');

// input fields in voucher modal
const acc_code_in_modal = document.querySelector('.acc_code_in_modal')
const head_in_modal = document.querySelector('.head_in_modal')
const notes_in_modal = document.querySelector('.notes_in_modal')
const receipt_no_in_modal = document.querySelector('.receipt_no_in_modal')
const chq_no_in_modal = document.querySelector('.chq_no_in_modal')
const amount_in_modal = document.querySelector('.amount_in_modal')
const bankSection = document.getElementById('bank-section');
const transaction_type = document.getElementById('transaction_type') // transaction effect for jv voucher like increase or decrease
const bank_select = document.getElementById('bank-select');
const remarks_in_modal = document.getElementById('remarks_in_modal');

// jv pro modal both cr and dr accounts
const jv_pro_modal = document.getElementById('journalVoucherModal');
const jv_pro_openBtn = document.getElementById('jv_pro_modal');
const jv_pro_closeBtn = document.getElementById('jv_pro_closeModal');
const jv_pro_cancelBtn = document.getElementById('jv_pro_cancelBtn');

if (cash_receipt_button){
    
    cash_receipt_button.addEventListener('click', () => openVoucherModal('CR'));
    cash_payment_button.addEventListener('click', () => openVoucherModal('CP'));
    bank_receipt_button.addEventListener('click', () => openVoucherModal('BR'));
    bank_payment_button.addEventListener('click', () => openVoucherModal('BP'));
    jv_button.addEventListener('click', () => openVoucherModal('JV'));
    closeBtn.addEventListener('click', closeModal);

    }


// Open modal function
function openModal() {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent body scroll when modal is open
}
// Close modal function
function closeModal() {
    modal.classList.remove('active');
    amount_in_modal.value = 0.00;
    document.body.style.overflow = '';
    bankSection.style.display = 'none' // Restore body scroll
    transaction_type.style.display = 'none' // Restore body scroll
}
const voucherConfig = {
    CR: {
        title: '🔌 CASH RECEIPT VOUCHER',
        requireAccount: true,
        notes :'CASH RCVD: '
    },
    CP: {
        title: '🔌 CASH PAYMENT VOUCHER',
        requireAccount: false,
        notes:'CASH PAID: '
    },
    BR: {
        title: '🔌 BANK RECEIPT VOUCHER',
        requireAccount: true,
        showbanks:true,
        notes:'BANK RCVD: '

    },
    BP: {
        title: '🔌 BANK PAYMENT VOUCHER',
        requireAccount: true,
        showbanks:true,
        notes:'BANK PAID: '
    },
    JV: {
        title: '🔌 JOURNAL VOUCHER',
        requireAccount: true,
        notes:'JV',
        showTransactionType :true
    }
};
function openVoucherModal(type) {
    const config = voucherConfig[type];

    if (config.requireAccount && !acc_code.value) {
        alert('Select account');
        return;
    }
    if (config.showTransactionType){
        transaction_type.style.display = 'block'
    }
    if (config.showbanks){
        bankSection.style.display = 'block'
    }
    acc_code_in_modal.value = acc_code.value || '';
    head_in_modal.value = head.value.trim();
    notes_in_modal.value = config.notes || ''
    voucher_type.innerText = config.title;
    hidden_voucher_type_value.value = type.trim()

    openModal();
}

if(document.getElementById('bank-select')){

    document.getElementById('bank-select').addEventListener('change', function () {
        const accCode = this.value;
        const accName = this.options[this.selectedIndex].text;
    
        console.log("Bank Acc Code:", accCode);
        console.log("Bank Name:", accName);
    });
}

if(save_voucher_modal_button){
    save_voucher_modal_button.addEventListener('click',()=>{
    const v_type = hidden_voucher_type_value.value
    const date = document.getElementById('vch_date').value
    console.log(date)
    let bank_acc_code = null;
    let jv_transaction_type = null;
    let jv_pro_cr_acc_code = null;
    const checkInModal = chq_no_in_modal.value || 0
    console.log(checkInModal)

    if (v_type == 'BR' || v_type ==='BP'){
        bank_acc_code = bank_select.value
        if(!bank_acc_code){
            alert('❌ Please select a bank account');
            bank_select.focus();
            return;
        }

    }

    if (v_type.toUpperCase() == 'JV'){
        const selected = document.querySelector('input[name="transaction_type"]:checked');

        if (!selected) {
            return alert('❌ Select Transaction Effect  '); // nothing selected
        }
        jv_transaction_type = selected.id

    }
    save_cash_voucher(v_type,acc_code_in_modal.value,
        head_in_modal.value.trim(),notes_in_modal.value,receipt_no_in_modal.value,
        checkInModal,amount_in_modal.value,voucher_modal_total.value,
        bank_acc_code,remarks_in_modal.value,jv_transaction_type,jv_pro_cr_acc_code,date)

    })
}

    
function save_cash_voucher(
    v_type,
    other_acc_code,
    other_acc_head,
    notes,
    receipt_no = 0 ,
    chq_no=0,
    amount,
    total,
    bank_acc_code = null,
    remarks_in_modal,
    jv_transaction_type = null,
    jv_pro_cr_acc_code = null,
    date = new Date().toISOString().split('T')[0],

    updateVoucher= false,
    vno =  0,
    dateent =null
    ) {
    let payload ={
            v_type: v_type,
            other_acc_code: other_acc_code,
            head: other_acc_head.trim(),
            notes: notes,
            receipt_no: receipt_no,
            chq_no: chq_no,
            amount:amount,
            total: total,
            remarks:remarks_in_modal,
            date :date,
            
    }
    if (bank_acc_code){
        payload.bank_acc_code = bank_acc_code
    }
    if(jv_transaction_type){
        payload.jv_transaction_type = jv_transaction_type
    }
    if(jv_pro_cr_acc_code){
        payload.jv_pro_cr_acc_code = jv_pro_cr_acc_code
    }
    if(updateVoucher){
        payload.updateVoucher = true;
        payload.vno = vno;
        payload.dateent = dateent;
    }

    if(!jv_pro_cr_acc_code && (amount_in_modal.value == 0 || !amount_in_modal.value || amount_in_modal.value == '0.00')){
        alert('Please fill the credentials')
        return;
    }
    fetch('/pos_accounts/save_voucher/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
    .then(res => {
        if (!res.ok) throw new Error('Server error');
        return res.json();
    })
    .then(data => {
        if (data.success) {
            alert('Voucher saved successfully ✅');
            amount_in_modal.value = '0.00'
            chq_no_in_modal.value = '0.00'
            
        } else {
            alert(data.message || 'Failed to save voucher');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Something went wrong');
    });
    }






document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && modal.classList.contains('active')) {
        closeModal();
    }
});

// Prevent modal content clicks from bubbling to overlay
if(document.querySelector('.modal-content')){

    document.querySelector('.modal-content').addEventListener('click', function(event) {
        event.stopPropagation();
    });
}


function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export default save_cash_voucher;