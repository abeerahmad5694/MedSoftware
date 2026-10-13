// Dynamic Voucher Modal - open/close functions
import myLedgerHelpers from "../services/helpers.js";
import { GlobalSearchModal } from '/static/mysearch/js/global_search_modal.js';
// import { openQuickAccountsModal } from "/static/myaccounts/js/modals/quick_accounts_modal.js";
const banksCombobox = document.getElementById("dvm_bank-select");
const datefield = document.getElementById("dvm_vch_date");
const dynamicVoucherSaveBtn = document.getElementById("dvm_voucher_modal_save_button");
const dvm_vch_no_el = document.getElementById('dvm_vch_no');
const dvm_hidden_voucher_type_value = document.getElementById("dvm_hidden_voucher_type_value");
const dvm_remarks_in_modal = document.getElementById("dvm_remarks_in_modal");
// const dvm_quick_account_button = document.getElementById("dvm_quick_account_button");

// Parent elements from ledger_modal
const parentAccCodeEl = document.getElementById("lm_ACC_CODE");
const parentAccNameEl = document.getElementById("lm_ACC_NAME");

if (dynamicVoucherSaveBtn) {
    dynamicVoucherSaveBtn.addEventListener("click", saveUpdateDynamicVoucher);
}

// Cancel and Delete buttons event listeners
const cancelBtn = document.querySelector(".dv-btn-cancel");
if (cancelBtn) {
    cancelBtn.addEventListener("click", function (e) {
        e.preventDefault();
        closeDynamicVoucherModal();
    });
}

const deleteBtn = document.querySelector(".dv-btn-delete");
if (deleteBtn) {
    deleteBtn.addEventListener("click", function (e) {
        e.preventDefault();
        const voucherType = dvm_hidden_voucher_type_value.value;
        const vno = dvm_vch_no_el.textContent.trim();
        if (!vno || vno === "0") {
            return alert("No voucher loaded to delete");
        }
        if (confirm("Are you sure you want to delete this voucher?")) {
            deleteDynamicVoucher(voucherType, vno);
        }
    });
}

const getSystemAccountCode = (key, fallback) => {
    if (window.getDefaultAccount) {
        return String(window.getDefaultAccount(key, fallback));
    }
    return String(fallback);
};

const VOUCHER_CONFIG = {
    CR: {
        title: '🔌 CASH RECEIPT VOUCHER',
        requireAccount: true,
        notes: 'CASH RCVD: ',
        get SYSTEM_ACCOUNT_CODES() { return getSystemAccountCode('default_cash_acc', '110000001'); }
    },
    CP: {
        title: '🔌 CASH PAYMENT VOUCHER',
        requireAccount: false,
        notes: 'CASH PAID: ',
        get SYSTEM_ACCOUNT_CODES() { return getSystemAccountCode('default_cash_acc', '110000001'); }
    },
    BR: {
        title: '🔌 BANK RECEIPT VOUCHER',
        requireAccount: true,
        showbanks: true,
        notes: 'BANK RCVD: ',
        get SYSTEM_ACCOUNT_CODES() { return getSystemAccountCode('default_bank_acc', '111000001'); }
    },
    BP: {
        title: '🔌 BANK PAYMENT VOUCHER',
        requireAccount: true,
        showbanks: true,
        notes: 'BANK PAID: ',
        get SYSTEM_ACCOUNT_CODES() { return getSystemAccountCode('default_bank_acc', '111000001'); }
    },
    ADJ: {
        title: '🔌 ADJUSTMENT VOUCHER',
        requireAccount: true,
        notes: 'ADJ',
        get SYSTEM_ACCOUNT_CODES() {
            return [
                getSystemAccountCode('sales_discount_acc', '330000001'),
                getSystemAccountCode('purchase_discount_acc', '430000001')
            ];
        }
    }
};

async function getAccountName(accCode) {
    if (!accCode || accCode === "0") return "";
    try {
        const response = await fetch(`/myaccounts/api/get/${parseInt(accCode)}/`);
        const data = await response.json();
        if (data && data.data && data.data.ACC_NAME) {
            return data.data.ACC_NAME;
        }
    } catch (e) {
        console.error(e);
    }
    return "";
}

// ─── Global Search Modal for row-level account search ───
// We keep a reference to the currently active row so onSelect fills the right row.
let _activeSearchRow = null;

GlobalSearchModal.init([{
    modalId: 'dvm_account_search',
    triggerSelector: null,          // we trigger programmatically
    triggerKey: null,
    title: 'Find Account',
    placeholder: 'Search by account head, name, code ...',
    appLabel: 'myaccounts',
    modelName: 'Accounts',
    primaryKey: 'ACC_CODE',
    indexdbStore: null,
    searchFields: ['ACC_CODE', 'ACC_NAME'],
    displayColumns: [
        { key: 'ACC_CODE', header: 'Code', width: '80px' },
        { key: 'ACC_NAME', header: 'Account Name' },
    ],
    excludeFilters: { 'TYPE__exact': 'Group' },
    pageSize: 50,
    onSelect: function(item) {
        if (_activeSearchRow) {
            const accCodeInput = _activeSearchRow.querySelector('.dvm_acc_code_in_modal');
            const headInput = _activeSearchRow.querySelector('.dvm_head_in_modal');
            if (accCodeInput) accCodeInput.value = item.ACC_CODE;
            if (headInput) headInput.value = item.ACC_NAME;
            checkAndAddEmptyRow();
        }
        _activeSearchRow = null;
    }
}]);

/**
 * Open the account search modal for a specific table row.
 * Called from the inline 🔍 button click or "O" key press on acc_code field.
 */
function openRowAccountSearch(row) {
    if (!row) return;
    _activeSearchRow = row;
    GlobalSearchModal.open('dvm_account_search');
}



// ─── Also wire the top-bar "Find A/C" button to search for the focused row ───
const findAccBtn = document.getElementById('dvm_btn-search-inVoucher');
if (findAccBtn) {
    findAccBtn.addEventListener('click', function (e) {
        e.preventDefault();
        // Use the first row if no row is focused
        const rows = document.querySelectorAll('.dv-table-wrapper tbody tr');
        const activeEl = document.activeElement;
        let targetRow = rows[0] || null;
        if (activeEl) {
            const closestRow = activeEl.closest('.dv-table-wrapper tbody tr');
            if (closestRow) targetRow = closestRow;
        }
        openRowAccountSearch(targetRow);
    });
}

function attachRowEventListeners(row) {
    const accCodeInput = row.querySelector('.dvm_acc_code_in_modal');
    const headInput = row.querySelector('.dvm_head_in_modal');
    const amountInput = row.querySelector('.dvm_amount_in_modal');

    if (accCodeInput) {
        accCodeInput.addEventListener('change', async function () {
            const accCode = this.value.trim();
            if (accCode) {
                const accName = await getAccountName(accCode);
                if (headInput) {
                    headInput.value = accName;
                }
            }
            checkAndAddEmptyRow();
        });

        // Open search modal on "O" key press in acc_code field
        accCodeInput.addEventListener('keydown', function (e) {
            if (e.key === 'o' || e.key === 'O') {
                // Only trigger if the field is empty or user explicitly presses O
                if (this.value.trim() === '') {
                    e.preventDefault();
                    openRowAccountSearch(row);
                }
            }
        });
    }

    if (amountInput) {
        amountInput.addEventListener('change', function () {
            updateTotalAmount();
            checkAndAddEmptyRow();
        });
        amountInput.addEventListener('input', function () {
            updateTotalAmount();
        });
    }

    // Wire up the inline search button for this row
    const searchBtn = row.querySelector('.dvm-search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function (e) {
            e.preventDefault();
            openRowAccountSearch(row);
        });
    }
}

function addDynamicVoucherRow() {
    const tbody = document.querySelector('.dv-table-wrapper tbody');
    if (!tbody) return;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><div class="dvm-acc-code-cell"><input type="text" class="dvm_acc_code_in_modal"/><button type="button" class="dvm-search-btn" title="Search Account (O)">🔍</button></div></td>
        <td><input type="text" class="dvm_head_in_modal" /></td>
        <td><input type="text" class="dvm_notes_in_modal"/></td>
        <td><input type="text" class="dvm_receipt_no_in_modal" value="0" /></td>
        <td><input type="text" class="dvm_chq_no_in_modal" value="0" /></td>
        <td><input type="text" class="dvm_amount_in_modal" value="0.00" /></td>
    `;
    tbody.appendChild(tr);
    attachRowEventListeners(tr);
}

function checkAndAddEmptyRow() {
    const rows = document.querySelectorAll('.dv-table-wrapper tbody tr');
    if (rows.length === 0) {
        addDynamicVoucherRow();
        return;
    }
    const lastRow = rows[rows.length - 1];
    const accCodeInput = lastRow.querySelector('.dvm_acc_code_in_modal');
    const amountInput = lastRow.querySelector('.dvm_amount_in_modal');

    if ((accCodeInput && accCodeInput.value.trim() !== '') || 
        (amountInput && parseFloat(amountInput.value) > 0)) {
        addDynamicVoucherRow();
    }
}

function updateTotalAmount() {
    const rows = document.querySelectorAll('.dv-table-wrapper tbody tr');
    let total = 0;
    rows.forEach(row => {
        const amountInput = row.querySelector('.dvm_amount_in_modal');
        if (amountInput) {
            const val = parseFloat(amountInput.value) || 0;
            total += val;
        }
    });

    const totalSection = document.querySelector('.dv-total-section');
    const totalAmountEl = document.querySelector('.dv-total-amount');
    if (totalAmountEl) {
        totalAmountEl.textContent = total.toFixed(2);
    }
    if (totalSection) {
        totalSection.style.display = total > 0 ? 'flex' : 'none';
    }
}

async function saveUpdateDynamicVoucher() {
    const voucherType = dvm_hidden_voucher_type_value.value;
    const vno = dvm_vch_no_el.textContent.trim();
    const date = datefield.value;

    if (!voucherType) {
        return alert("Please Select a Voucher Type");
    }

    if (!date) {
        return alert("Please select a date");
    }

    const remarks = dvm_remarks_in_modal.value;
    const bank = banksCombobox ? banksCombobox.value : "";

    // Bank validation
    if ((voucherType === 'BP' || voucherType === 'BR') && !bank) {
        return alert('Please select a bank');
    }

    // ADJ transaction type validation
    let transactionType = null;
    if (voucherType === 'ADJ') {
        const selectedRadio = document.querySelector('input[name="dvm_transaction_type"]:checked');
        transactionType = selectedRadio ? selectedRadio.id : null;
        if (!transactionType) {
            return alert('Please select a transaction type');
        }
    }

    const rows = document.querySelectorAll('.dv-table-wrapper tbody tr');
    const listOfVoucherLines = [];

    for (let i = 0; i < rows.length; i++) {
        const c = rows[i].cells;
        const accCode = c[0].querySelector('.dvm_acc_code_in_modal').value.trim();
        const amount = c[5].firstElementChild.value.trim();

        if (!accCode || amount === '0.00' || amount === '') {
            continue;
        }

        // Determine refAccCode based on voucher type and settings
        let refAccCode = window.getDefaultAccount ? String(window.getDefaultAccount('default_cash_acc', '110000001')) : "110000001"; // Cash in Hand
        if (voucherType === "BR" || voucherType === "BP") {
            refAccCode = bank || (window.getDefaultAccount ? String(window.getDefaultAccount('default_bank_acc', '111000001')) : "111000001");
        } else if (voucherType === "ADJ") {
            const defaultPurDisc = window.getDefaultAccount ? String(window.getDefaultAccount('purchase_discount_acc', '430000001')) : "430000001";
            const defaultSalesDisc = window.getDefaultAccount ? String(window.getDefaultAccount('sales_discount_acc', '330000001')) : "330000001";
            refAccCode = transactionType === "dvm_lessInSup" ? defaultPurDisc : defaultSalesDisc;
        }

        listOfVoucherLines.push({
            accCode,
            head: c[1].firstElementChild.value.trim(),
            notes: c[2].firstElementChild.value.trim(),
            receiptNo: c[3].firstElementChild.value.trim(),
            chqNo: c[4].firstElementChild.value.trim(),
            amount,
            refAccCode,
        });
    }

    if (!listOfVoucherLines.length) {
        return alert("Please Enter At Least One Voucher Line");
    }

    const payload = {
        date,
        voucherType,
        remarks,
        listOfVoucherLines
    };

    if (vno && vno !== "0") {
        payload.vno = vno;
        payload.update = true;
    }

    if (voucherType === 'BP' || voucherType === 'BR') {
        payload.bank = bank;
    } else if (voucherType === 'ADJ') {
        payload.transactionType = transactionType;
    }

    try {
        const response = await myLedgerHelpers.saveUpdateDynamicVoucher(payload);
        alert(response.message);
        if (response.success) {
            // Print/Preview the voucher after save
            const savedVno = response.vno || vno;
            if (savedVno && savedVno !== "0" && window.DocumentPrinter) {
                const vouchert = voucherType === 'ADJ' ? 'JV' : voucherType
                const billNumber = `${vouchert}-${savedVno}`;
                console.log('billNumber', billNumber)
                window.DocumentPrinter.printDocument({
                    bill_no: billNumber,
                    model_name: "Gledg",
                    page_type: window.companyConfigurations?.vouchers?.default_page_size || "a4",
                    document_type: "voucher",
                    data_source: "server",
                    allow_multiple_print: false,
                    copies: 1,
                });
            }

            // const isModal = document.querySelector('.dv-modal-overlay');
            // closeDynamicVoucherModal();
            // if(!isModal){
            //     const url = window.location.pathname
            //     let not_modal = false
            //     if (url.split('/').length < 4){
            //         not_modal = true
            //     }
            //     // Refresh parent ledger if function exists
            //     if (window.refreshLedger) {
            //         window.refreshLedger();
            //     } else {
            //         const url = window.location.pathname
            //         const last = url.replace(/\/\d+\/?$/, '/')
            //         window.location.href = last
            //     }
            // }

        }
    } catch (err) {
        console.error(err);
        alert("Server Error");
    }
}
const GenerateBtn = document.getElementById('lm_generateBtn');
export async function deleteDynamicVoucher(voucherType, vno) {
    try {
        const response = await myLedgerHelpers.deleteDynamicVoucher({
            voucherType,
            vno
        });
        alert(response.message);
        if (response.success) {
            closeDynamicVoucherModal();
            if(GenerateBtn){
                GenerateBtn.click();
            }
            // if (window.refreshLedger) {
            //     window.refreshLedger();
            // } else {
            //     window.location.reload();
            // }
        }
    } catch (error) {
        console.error(error);
        alert("Server Error");
    }
}

export async function openDynamicVoucherModal(voucherType, vno = null) {
    resetDynamicVoucherModal();
    console.log('ahere')

    const overlay = document.getElementById('dynamicVoucherModalOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.add('active');
        // Register with ModalStack so Esc only closes the topmost modal
        if (window.ModalStack) {
            window.ModalStack.push('dynamicVoucherModal', () => closeDynamicVoucherModal());
        }
    }

    // Title
    const titleEl = document.getElementById('dvm_voucher_type');
    if (titleEl) {
        titleEl.innerText = VOUCHER_CONFIG[voucherType].title || 'DYNAMIC VOUCHER';
    }
    if(!(VOUCHER_CONFIG[voucherType])){
        return alert("Invalid Voucher Type");
    }

    // Default fields
    dvm_hidden_voucher_type_value.value = voucherType;
    dvm_vch_no_el.textContent = vno || "0";
    datefield.value = new Date().toISOString().split("T")[0];

    // Sections
    toggleVoucherSections(voucherType);

    // Bank loading
    if (voucherType === 'BR' || voucherType === 'BP') {
        await loadBanks();
    }

    // Edit mode or create mode
    if (vno) {
        const responseObj = await myLedgerHelpers.getDynamicVoucherForEdit(vno, voucherType);
        
        if (responseObj && responseObj.success && responseObj.data && responseObj.data.length > 0) {
            const rawLines = responseObj.data;
            const firstEntry = rawLines[0];

            const formattedData = {
                date: firstEntry.DATE || "",
                remarks: firstEntry.REMARKS || "",
                lines: []
            };

            // Filter out system balancing lines to get user lines
            const userLines = rawLines.filter(line => {
                const acc = String(line.ACC_CODE);
                if (voucherType === 'CR' || voucherType === 'CP') {
                    return acc !== VOUCHER_CONFIG[voucherType].SYSTEM_ACCOUNT_CODES;
                } else if (voucherType === 'BR' || voucherType === 'BP') {
                    return acc !== VOUCHER_CONFIG[voucherType].SYSTEM_ACCOUNT_CODES;
                } else if (voucherType === 'ADJ') {
                    return !VOUCHER_CONFIG[voucherType].SYSTEM_ACCOUNT_CODES.includes(acc);
                } else {
                    return acc !== '110000001';
                }
            });

            if ((voucherType === 'BR' || voucherType === 'BP') && userLines.length > 0) {
                formattedData.bank = String(userLines[0].REF_ACC_CODE);
            }

            formattedData.lines = await Promise.all(userLines.map(async line => {
                const accCode = String(line.ACC_CODE);
                const head = String(line.ACC_HEAD);
                return {
                    accCode,
                    head,
                    notes: line.DESCRIPTION || "",
                    receiptNo: line.RECEIPTNO || 0,
                    chqNo: line.CHQNO || 0,
                    amount: line.AMOUNT || "0.00"
                };
            }));

            // Handle ADJ radio button selection on load
            if (voucherType === 'ADJ' && userLines.length > 0) {
                const userAmtType = userLines[0].AMT_TYPE;
                if (userAmtType === 'DR') {
                    const supRadio = document.getElementById('dvm_lessInSup');
                    if (supRadio) supRadio.checked = true;
                } else {
                    const cusRadio = document.getElementById('dvm_lessInCus');
                    if (cusRadio) cusRadio.checked = true;
                }
            }

            fillDynamicVoucherModal(formattedData);
        } else {
            alert("Failed to load voucher or voucher empty.");
        }
    } else {
        // Create mode: Check if account selected in parent ledger
        const parentAccCode = parentAccCodeEl ? parentAccCodeEl.value.trim() : "";
        const parentAccName = parentAccNameEl ? parentAccNameEl.value.trim() : "";

        // if (overlay && (!parentAccCode || parentAccCode === "0")) {
        //     alert("Please select an account first");
        //     closeDynamicVoucherModal();
        //     return;
        // }

        // Fill the first row with parent account info if available
        const rows = document.querySelectorAll('.dv-table-wrapper tbody tr');
        if (rows.length > 0 && parentAccCode && parentAccCode !== "0") {
            const firstRow = rows[0];
            const accCodeInput = firstRow.querySelector('.dvm_acc_code_in_modal');
            const headInput = firstRow.querySelector('.dvm_head_in_modal');
            const notesInput = firstRow.querySelector('.dvm_notes_in_modal');
            if (accCodeInput) accCodeInput.value = parentAccCode;
            if (headInput) headInput.value = parentAccName;
            if (notesInput) notesInput.value = VOUCHER_CONFIG[voucherType].notes || "";
        }
    }
}

function fillDynamicVoucherModal(data) {
    if (!data) return;

    datefield.value = data.date || "";
    dvm_remarks_in_modal.value = data.remarks || "";

    if (data.bank && banksCombobox) {
        banksCombobox.value = data.bank;
    }

    const tbody = document.querySelector('.dv-table-wrapper tbody');
    if (tbody) {
        tbody.innerHTML = "";
    }

    if (Array.isArray(data.lines)) {
        data.lines.forEach((line, index) => {
            addDynamicVoucherRow();
            const row = document.querySelectorAll('.dv-table-wrapper tbody tr')[index];
            const accCodeInput = row.querySelector('.dvm_acc_code_in_modal');
            const headInput = row.querySelector('.dvm_head_in_modal');
            const notesInput = row.querySelector('.dvm_notes_in_modal');
            const receiptInput = row.querySelector('.dvm_receipt_no_in_modal');
            const chqInput = row.querySelector('.dvm_chq_no_in_modal');
            const amountInput = row.querySelector('.dvm_amount_in_modal');

            if (accCodeInput) accCodeInput.value = line.accCode || '';
            if (headInput) headInput.value = line.head || '';
            if (notesInput) notesInput.value = line.notes || '';
            if (receiptInput) receiptInput.value = line.receiptNo || '0';
            if (chqInput) chqInput.value = line.chqNo || '0';
            if (amountInput) amountInput.value = line.amount || '0.00';
        });
    }

    updateTotalAmount();
    checkAndAddEmptyRow();
}

function toggleVoucherSections(voucherType) {
    const bankSec = document.getElementById('dvm_bank-section');
    const txnSec = document.getElementById('dvm_transaction_type');

    if (bankSec) {
        bankSec.style.display = ['BR', 'BP'].includes(voucherType) ? 'block' : 'none';
    }

    if (txnSec) {
        txnSec.style.display = voucherType === 'ADJ' ? 'block' : 'none';
    }
}

async function loadBanks() {
    const banks = await myLedgerHelpers.getBanks();
    if (!banks || !banksCombobox) return;

    banksCombobox.innerHTML = '<option value="">-- Select Bank --</option>';

    banks.forEach(bank => {
        const option = document.createElement('option');
        option.value = bank.ACC_CODE;
        option.textContent = bank.ACC_NAME;
        banksCombobox.appendChild(option);
    });
}

function resetDynamicVoucherModal() {
    dvm_vch_no_el.textContent = "0";
    datefield.value = "";
    dvm_remarks_in_modal.value = "";

    if (banksCombobox) {
        banksCombobox.value = "";
    }

    const ADJSupRadio = document.getElementById('dvm_lessInSup');
    const ADJCusRadio = document.getElementById('dvm_lessInCus');
    if (ADJSupRadio) ADJSupRadio.checked = false;
    if (ADJCusRadio) ADJCusRadio.checked = false;

    // Clear rows and put 4 empty default rows
    const tbody = document.querySelector('.dv-table-wrapper tbody');
    if (tbody) {
        tbody.innerHTML = "";
        for (let i = 0; i < 2; i++) {
            addDynamicVoucherRow();
        }
    }
    updateTotalAmount();``
}

function closeDynamicVoucherModal() {
    const overlay = document.getElementById('dynamicVoucherModalOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        if (window.ModalStack) window.ModalStack.pop('dynamicVoucherModal');
    }
}





// dvm_quick_account_button.addEventListener("click", function (e) {
//     e.preventDefault();
//     openQuickAccountsModal();
// });










// Close on overlay click
const dvOverlay = document.getElementById('dynamicVoucherModalOverlay');
if (dvOverlay) {
    dvOverlay.addEventListener('click', function (e) {
        if (e.target === this) closeDynamicVoucherModal();
    });
}
// Close on button click
const dvCloseBtn = document.getElementById('dv_modal_close_button');
if (dvCloseBtn) {
    dvCloseBtn.addEventListener('click', function () {
        
        closeDynamicVoucherModal();
    });
}

// Escape is handled globally by ModalStack (global_search_modal.js).
// ModalStack.closeTop() calls closeDynamicVoucherModal() via the registered callback.

// Auto-load if in page form mode
document.addEventListener("DOMContentLoaded", () => {
    const pageWrapper = document.getElementById("dynamicVoucherPageWrapper");
    if (pageWrapper) {
        const vtype = pageWrapper.getAttribute("data-vtype") || "CR";
        const vno = pageWrapper.getAttribute("data-vno");
        openDynamicVoucherModal(vtype, vno && vno !== "None" ? parseInt(vno) : null);
    }
});