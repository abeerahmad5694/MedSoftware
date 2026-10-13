import { GlobalSearchModal } from '/static/mysearch/js/global_search_modal.js';
import myLedgerHelpers from "/static/myledger/js/services/helpers.js";


import { deleteDynamicVoucher } from "./dynamic_voucher_modal.js";

GlobalSearchModal.init([{
    modalId: 'jvm_btn-search-drAccount',
    triggerSelector: '#jvm_btn-search-drAccount',
    triggerKey: null,                    // optional hotkey
    title: 'Find Debit Account',
    placeholder: 'Search by account head, name, code ...',
    appLabel: 'myaccounts',
    modelName: 'Accounts',
    primaryKey: 'ACC_CODE',
    indexdbStore: null,            // null = skip local
    searchFields: ['ACC_CODE', 'ACC_NAME'],
    displayColumns: [
        { key: 'ACC_CODE', header: 'Code', width: '80px' },
        { key: 'ACC_NAME', header: 'Account Name' },
    ],
    excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
    pageSize: 50,
    onSelect: function (item) {
        const drCodeInput = document.getElementById('jvm_acc_code_dr');
        const drNameInput = document.getElementById('jvm_acc_head_dr');
        const drIdInput = document.getElementById('jvm_account_from_id');

        if (drCodeInput) drCodeInput.value = item.ACC_CODE;
        if (drNameInput) drNameInput.value = item.ACC_NAME;
        if (drIdInput) drIdInput.value = item.ACC_CODE;
    }
},
{
    modalId: 'jvm_btn-search-crAccount',
    triggerSelector: '#jvm_btn-search-crAccount',
    triggerKey: null,                    // optional hotkey
    title: 'Find Credit Account',
    placeholder: 'Search by account head, name, code ...',
    appLabel: 'myaccounts',
    modelName: 'Accounts',
    primaryKey: 'ACC_CODE',
    indexdbStore: null,            // null = skip local
    searchFields: ['ACC_CODE', 'ACC_NAME'],
    displayColumns: [
        { key: 'ACC_CODE', header: 'Code', width: '80px' },
        { key: 'ACC_NAME', header: 'Account Name' },
    ],
    excludeFilters: { 'TYPE__exact': 'Group' },   // exclude from local results
    pageSize: 50,
    onSelect: function (item) {
        const drCodeInput = document.getElementById('jvm_acc_code_cr');
        const drNameInput = document.getElementById('jvm_acc_head_cr');
        const drIdInput = document.getElementById('jvm_account_to_id');

        if (drCodeInput) drCodeInput.value = item.ACC_CODE;
        if (drNameInput) drNameInput.value = item.ACC_NAME;
        if (drIdInput) drIdInput.value = item.ACC_CODE;
    }
}]);

// Initialize date to today's date if empty
const dateInput = document.getElementById('jvm_date');
if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
}

const saveJvVoucherBtn = document.getElementById('jvm_saveBtn');
if (saveJvVoucherBtn) {
    saveJvVoucherBtn.addEventListener('click', () => saveJvVoucher());
}

async function saveJvVoucher() {
    console.log('called saveJvVoucher');
    try {
        const date = document.getElementById('jvm_date')?.value;
        const acc_from_id = document.getElementById('jvm_account_from_id')?.value;
        const acc_to_id = document.getElementById('jvm_account_to_id')?.value;
        const amount = document.getElementById('jvm_amount')?.value;
        const notes = document.getElementById('jvm_notes')?.value || "";
        const chqno = document.getElementById('jvm_chqno')?.value || 0;
        const receiptno = document.getElementById('jvm_receiptno')?.value || 0;
        const vno = document.getElementById('jvm_vno')?.value || "";
        const acc_head_cr = document.getElementById('jvm_acc_head_cr').value || '';
        const acc_head_dr = document.getElementById('jvm_acc_head_dr').value || '';
        // Client-side validations
        if (!date) {
            alert("Please select a date.");
            return;
        }
        if (!acc_from_id) {
            alert("Please select a Debit Account.");
            return;
        }
        if (!acc_to_id) {
            alert("Please select a Credit Account.");
            return;
        }
        if (acc_from_id === acc_to_id) {
            alert("Debit and Credit Accounts must be different.");
            return;
        }
        if (!amount || parseFloat(amount) <= 0) {
            alert("Please enter a valid amount greater than zero.");
            return;
        }

        const payload = {
            acc_from_id: acc_from_id,
            acc_head_dr: acc_head_dr,
            acc_to_id: acc_to_id,
            acc_head_cr: acc_head_cr,
            voucherType: 'JV',
            date: date,
            notes: notes,
            amount: amount,
            chqno: chqno,
            receiptno: receiptno,
        };

        if (vno) {
            payload.vno = vno;
            payload.update = true;
        }

        // console.log("Saving JV Voucher Payload:", payload);
        const response = await myLedgerHelpers.saveUpdateDynamicVoucher(payload);
        console.log('response', response)
        if (response.success) {
            // alert(response.message || 'Voucher saved successfully!');

            // Print/Preview the JV voucher after save
            const savedVno = response.vno || vno;
            console.log('savevno', savedVno)
            if (savedVno) {
                console.log('skfjsdkfjslkdfjlsdkfjlskdfjlsdjfldj')
                console.log('window.DocumentPrinter', window.DocumentPrinter)
                window.DocumentPrinter.printDocument({
                    bill_no: `JV-${savedVno}`,
                    model_name: "Gledg",
                    page_type: (window.companyConfigurations?.vouchers?.default_page_size || "a4").toLowerCase(),
                    document_type: "voucher",
                    data_source: "server",
                    allow_multiple_print: false,
                    copies: 1,
                }).catch((printError) => {
                    console.error("Voucher saved, but print preview failed:", printError);
                });


            }

            const isModal = document.querySelector('.jvm-modal-overlay');
            closeJvVoucherModal();
            // if(!isModal){
            //     const url = window.location.pathname
            //     const last = url.replace(/\/\d+\/?$/, '/')
            //     window.location.href = last
            // }
        } else {
            alert(response.error || 'Failed to save voucher.');
        }
    } catch (error) {
        console.error('Error saving JV voucher:', error);
        alert('Server Error occurred while saving voucher.');
    }
}



// const dvm_hidden_voucher_type_value = document.getElementById("dvm_hidden_voucher_type_value");
const deleteBtn = document.getElementById("delete_voucher_btn");
const vnoEl = document.getElementById("jvm_vno");
if (deleteBtn && vnoEl) {
    deleteBtn.addEventListener("click", function (e) {
        e.preventDefault();
        // const voucherType = dvm_hidden_voucher_type_value.value;
        const vno = vnoEl.value;
        if (!vno || vno === "0") {
            return alert("No voucher loaded to delete");
        }
        if (confirm("Are you sure you want to delete this voucher?")) {
            deleteDynamicVoucher('JV', vno);
        }
    });
}
else {
    console.error('delete_voucher_button not found');
}




// // Helper to get Account Name by Code
// async function getAccountName(accCode) {
//     if (!accCode || accCode === "0") return "";
//     try {
//         const response = await fetch(`/myaccounts/api/get/${parseInt(accCode)}/`);
//         const data = await response.json();
//         if (data && data.data && data.data.ACC_NAME) {
//             return data.data.ACC_NAME;
//         }
//     } catch (e) {
//         console.error(e);
//     }
//     return "";
// }

// Reset modal fields
function resetJvVoucherModal() {
    const fields = [
        'jvm_vno', 'jvm_account_from_id', 'jvm_account_to_id', 'jvm_amount',
        'jvm_notes', 'jvm_chqno', 'jvm_receiptno', 'jvm_acc_code_dr',
        'jvm_acc_head_dr', 'jvm_acc_code_cr', 'jvm_acc_head_cr'
    ];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    const dateEl = document.getElementById('jvm_date');
    if (dateEl) {
        dateEl.value = new Date().toISOString().split('T')[0];
    }
}

// JV Voucher Modal - open/close functions
export async function openJvVoucherModal(vno = null, voucherType = 'JV') {
    resetJvVoucherModal();

    var overlay = document.getElementById('jvVoucherModalOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.add('active');
        // Register with ModalStack so Esc only closes the topmost modal
        if (window.ModalStack) {
            window.ModalStack.push('jvVoucherModal', () => closeJvVoucherModal());
        }
    }

    const vnoEl = document.getElementById('jvm_vno');
    if (vnoEl) vnoEl.value = vno || "";

    const vtypeEl = document.getElementById('jvm_v_type');
    if (vtypeEl) vtypeEl.value = voucherType;

    if (vno) {
        try {
            const responseObj = await myLedgerHelpers.getDynamicVoucherForEdit(vno, voucherType);
            if (responseObj && responseObj.success && responseObj.data && responseObj.data.length > 0) {
                const rawLines = responseObj.data;
                const drLine = rawLines.find(line => line.AMT_TYPE === 'DR');
                const crLine = rawLines.find(line => line.AMT_TYPE === 'CR');

                if (drLine && crLine) {
                    const dateInput = document.getElementById('jvm_date');
                    if (dateInput && drLine.DATE) {
                        dateInput.value = drLine.DATE;
                    }

                    // Set Debit Account details
                    const drCodeInput = document.getElementById('jvm_acc_code_dr');
                    const drNameInput = document.getElementById('jvm_acc_head_dr');
                    const drIdInput = document.getElementById('jvm_account_from_id');
                    if (drCodeInput) drCodeInput.value = drLine.ACC_CODE;
                    if (drIdInput) drIdInput.value = drLine.ACC_CODE;
                    if (drNameInput) drNameInput.value = drLine.ACC_HEAD || 'System Account';

                    // Set Credit Account details
                    const crCodeInput = document.getElementById('jvm_acc_code_cr');
                    const crNameInput = document.getElementById('jvm_acc_head_cr');
                    const crIdInput = document.getElementById('jvm_account_to_id');
                    if (crCodeInput) crCodeInput.value = crLine.ACC_CODE;
                    if (crIdInput) crIdInput.value = crLine.ACC_CODE;
                    if (crNameInput) crNameInput.value = crLine.ACC_HEAD || 'System Account';

                    // Set remaining fields
                    const amountInput = document.getElementById('jvm_amount');
                    if (amountInput) amountInput.value = drLine.AMOUNT;

                    const notesInput = document.getElementById('jvm_notes');
                    if (notesInput) notesInput.value = drLine.DESCRIPTION || "";

                    const chqnoInput = document.getElementById('jvm_chqno');
                    if (chqnoInput) chqnoInput.value = drLine.CHQNO || "";

                    const receiptnoInput = document.getElementById('jvm_receiptno');
                    if (receiptnoInput) receiptnoInput.value = drLine.RECEIPTNO || "";
                } else {
                    alert("Invalid JV Voucher data structure on backend.");
                }
            } else {
                alert("Voucher details not found on the server.");
            }
        } catch (error) {
            console.error("Error fetching JV voucher for edit:", error);
            alert("Error loading JV voucher details.");
        }
    }
}


const GenerateBtn = document.getElementById('lm_generateBtn');

function closeJvVoucherModal() {
    var overlay = document.getElementById('jvVoucherModalOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        // if(GenerateBtn){
        //     GenerateBtn.click();
        // }
        // if (window.ModalStack) window.ModalStack.pop('jvVoucherModal');
    }
}

// Expose open and close to window for inline onclick attributes
// window.openJvVoucherModal = openJvVoucherModal;
// window.closeJvVoucherModal = closeJvVoucherModal;

// Close on overlay click
var jvOverlay = document.getElementById('jvVoucherModalOverlay');
if (jvOverlay) {
    jvOverlay.addEventListener('click', function (e) {
        if (e.target === this) closeJvVoucherModal();
    });
}

var jvmCloseBtn = document.getElementById('jvm-closeBtn');
if (jvmCloseBtn) {
    jvmCloseBtn.addEventListener('click', closeJvVoucherModal);
}

// Cancel button
var jvCancelBtn = document.getElementById('jvm_cancelBtn');
if (jvCancelBtn) {
    console.log('click')
    jvCancelBtn.addEventListener('click', closeJvVoucherModal);
}

// Escape is handled globally by ModalStack (global_search_modal.js).
// ModalStack.closeTop() calls closeJvVoucherModal() via the registered callback.

// Auto-load if in page form mode
document.addEventListener("DOMContentLoaded", () => {
    const pageWrapper = document.getElementById("jvVoucherPageWrapper");
    if (pageWrapper) {
        const vtype = pageWrapper.getAttribute("data-vtype") || "JV";
        const vno = pageWrapper.getAttribute("data-vno");
        openJvVoucherModal(vno && vno !== "None" ? parseInt(vno) : null, vtype);
    }
});
