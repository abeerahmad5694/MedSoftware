import {Helpers} from "/static/myaccounts/js/services/account_utils.js"
import {openAccountModal} from "/static/myaccounts/js/modals/global_account_form_modal.js"

export async function create_quick_account(partyType){
    let parentCode = null
    if(partyType=='client'){
        parentCode = 112
    }
    else if(partyType=='supplier'){
        parentCode = 231
    }
    else if(partyType=='general_expense'){
        parentCode = 321
    }
    else if(partyType=='bank'){
        parentCode = 111
    }
    
    const level = 4
    const data = await Helpers.getNextAccountCode(parentCode,level)
    if(data.success == false){
        return alert(data.message)
    }
    openAccountModal(data.next_acc_code,level)
}

// Expose to window for inline HTML onclick handlers
window.create_quick_account = create_quick_account;
window.create_quic_account = create_quick_account;

// Export modal control functions
export function openQuickAccountsModal() {
    const overlay = document.getElementById('quickAccountsModalOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.add('active');
        if (window.ModalStack) {
            window.ModalStack.push('quickAccountsModal', () => closeQuickAccountsModal());
        }
    }
}

export function closeQuickAccountsModal() {
    const overlay = document.getElementById('quickAccountsModalOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        if (window.ModalStack) {
            window.ModalStack.pop('quickAccountsModal');
        }
    }
}

// window.openQuickAccountsModal = openQuickAccountsModal;
// // window.closeQuickAccountsModal = closeQuickAccountsModal;

// Bind event listeners if elements exist
// document.addEventListener('DOMContentLoaded', () => {
const btnClient = document.getElementById('btnClientOpen');
const btnSupplier = document.getElementById('btnSupplierOpen');
const btnExpense = document.getElementById('btnExpenseOpen');
const btnBank = document.getElementById('btnBankOpen');
const btnClose = document.getElementById('qa_modal_close_button');

if (btnClient) {
    btnClient.addEventListener('click', (e) => {
        e.preventDefault();
        create_quick_account('client');
    });
}
if (btnSupplier) {
    btnSupplier.addEventListener('click', (e) => {
        e.preventDefault();
        create_quick_account('supplier');
    });
}
if (btnExpense) {
    btnExpense.addEventListener('click', (e) => {
        e.preventDefault();
        create_quick_account('general_expense');
    });
}
if (btnBank) {
    btnBank.addEventListener('click', (e) => {
        e.preventDefault();
        create_quick_account('bank');
    });
}
if (btnClose) {
    btnClose.addEventListener('click', (e) => {
        e.preventDefault();
        closeQuickAccountsModal();
    });
}
// });