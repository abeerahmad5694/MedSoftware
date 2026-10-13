import myLedgerHelpers from '/static/myledger/js/services/helpers.js'
import { GlobalSearchModal } from '/static/mysearch/js/global_search_modal.js';
import { openAccountModal } from "/static/myaccounts/js/modals/global_account_form_modal.js";
import { openDynamicVoucherModal} from "/static/myledger/js/modals/dynamic_voucher_modal.js";
import { openJvVoucherModal } from "/static/myledger/js/modals/jv_voucher_modal.js";

const GenerateBtn = document.getElementById('lm_generateBtn');
const ledgerBody = document.getElementById('lm_ledger-body');
const searchAccCodeBtn = document.getElementById('lm_SEARCH_ACC_CODE');
const accountProfileBtn = document.getElementById('lm_ACCOUNT_PROFILE_BTN');
const API_GET = (ACC_CODE) => `/myaccounts/api/get/${ACC_CODE}/`;


// Event listeners for opening modal from general ledger
const crBtn = document.getElementById("lm_btn-cr");
const cpBtn = document.getElementById("lm_btn-cp");
const brBtn = document.getElementById("lm_btn-br");
const bpBtn = document.getElementById("lm_btn-bp");
const ADJBtn = document.getElementById("lm_btn-ADJ");
const closeBtn = document.getElementById("dv_modal_close_button");
const dateFrom = document.getElementById('lm_DATE_FROM');
const dateTo = document.getElementById('lm_DATE_TO');

if (crBtn) crBtn.addEventListener("click", () => openDynamicVoucherModal("CR"));
if (cpBtn) cpBtn.addEventListener("click", () => openDynamicVoucherModal("CP"));
if (brBtn) brBtn.addEventListener("click", () => openDynamicVoucherModal("BR"));
if (bpBtn) bpBtn.addEventListener("click", () => openDynamicVoucherModal("BP"));
if (ADJBtn) ADJBtn.addEventListener("click", () => openDynamicVoucherModal("ADJ"));

// if (closeBtn) closeBtn.addEventListener("click", closeDynamicVoucherModal);
dateFrom.value = new Date(new Date().getTime() - (365 * 24 * 60 * 60 * 1000)).toISOString().slice(0, 10);// one year befoore
dateTo.value = new Date(new Date().getTime()+(365 * 24 * 60 * 60 * 1000)).toISOString().slice(0, 10);

GlobalSearchModal.init([
    {
        modalId: 'lm_SEARCH_ACC_CODE',
        triggerSelector: '#lm_SEARCH_ACC_CODE',
        triggerKey: null,                    // optional hotkey
        title: 'Find Account',
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
        onSelect: async (item) => {
            const lmCodeInput = document.getElementById('lm_ACC_CODE');
            const lmNameInput = document.getElementById('lm_ACC_NAME');
            const response = await fetch(API_GET(item.ACC_CODE));
            if (!response.ok) return alert('There is something wrong with get api');
            const data = await response.json();
            if (!data.success) return alert(data.message)
            for (let key in data.data) {
                if (document.getElementById(`lm_${key}`)) {
                    document.getElementById(`lm_${key}`).value = data.data[key];
                }
                
            }
            GenerateBtn?.click();
            document.getElementById('lm_ACC_CODE').focus();

            
        }
    },

]);


document.getElementById('lm_ACC_CODE').addEventListener('keydown',(e)=>{
    if (e.key === 'Tab') {
        e.preventDefault();
        document.getElementById('lm_SEARCH_ACC_CODE').click();
    }
});
if (accountProfileBtn) accountProfileBtn.addEventListener('click', function () {
    console.log('cliked')
    const accCode = document.getElementById('lm_ACC_CODE').value;
    if (!accCode || accCode == 0) return alert('Please enter account code');
    openAccountModal(parseInt(accCode), 4);
})
else console.log('No account profile button found');

if (GenerateBtn) GenerateBtn.addEventListener('click', function () {
    const accCode = document.getElementById('lm_ACC_CODE').value;
    const dateFrom = document.getElementById('lm_DATE_FROM').value;
    const dateTo = document.getElementById('lm_DATE_TO').value;
    if (!accCode || accCode == 0) return alert('Please enter account code');
    generateLedger(parseInt(accCode), dateFrom, dateTo)
    // console.log(accCode, dateFrom, dateTo);
});



document.addEventListener('DOMContentLoaded',()=>{
    
  const urlParams = new URLSearchParams(window.location.search);
  const acc_code = urlParams.get("acc_code");
//   const convertIntoBill = urlParams.get('convertIntoBill') || 0

  // console.log('ulparams',urlParams)
  if (acc_code) {
    document.getElementById('lm_ACC_CODE').value = acc_code;
    GenerateBtn?.click();
  }

})



async function generateLedger(accCode, fromDate, toDate) {
    const data = await myLedgerHelpers.getGeneralLedger(accCode, fromDate, toDate);
    if (data.success) {
        createLedgerRows(data.data);

        // Update footer totals
        const drEl = document.querySelector('.dr-val');
        const crEl = document.querySelector('.cr-val');
        const balEl = document.querySelector('.bal-val');

        if (drEl) {
            const drVal = parseFloat(data.total_debit || 0);
            drEl.textContent = drVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        if (crEl) {
            const crVal = parseFloat(data.total_credit || 0);
            crEl.textContent = crVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        if (balEl) {
            balEl.textContent = data.closing_balance || '0.00 Dr';
        }
        // return alert(data.message)
        // console.log(data);
    } else {
        return alert(data.message)
    }
}


const voucherType = document.getElementById("lm_voucher-type");
const descInput = document.querySelector(".desc-input");

voucherType.addEventListener("change", filterLedger);
descInput.addEventListener("input", filterLedger);

function filterLedger() {
    const selectedType = voucherType.value.trim().toUpperCase();
    const searchText = descInput.value.trim().toLowerCase();

    const rows = document.querySelectorAll("#lm_ledger-body tr");

    rows.forEach(row => {
        // Skip empty rows if you have them
        if (row.classList.contains("empty-row")) return;

        const vType = row.cells[0]?.textContent.trim().toUpperCase() || "";
        const description = row.cells[3]?.textContent.trim().toLowerCase() || "";

        const typeMatch =
            !selectedType || vType === selectedType;

        const descMatch =
            !searchText || description.includes(searchText);

        row.style.display = (typeMatch && descMatch) ? "" : "none";
    });
}


function createLedgerRows(data) {

    ledgerBody.innerHTML = '';
    data.forEach(row => {
        const tr = document.createElement('tr');
        // If it's the Opening Balance row, don't make the empty VNO clickable
        const vnoCell = row.VNO
            ? `<td data-vtype="${row.V_TYPE}" data-vno="${row.VNO}">${row.VNO}</td>`
            : `<td></td>`;

        tr.innerHTML = `
            <td>${row.V_TYPE || ''}</td>
            <td>${row.DATE}</td>
            ${vnoCell}
            <td>${row.DESCRIPTION || ''}</td>
            <td>${row.AMOUNT || ''}</td>
            <td>${row.DEBIT || ''}</td>
            <td>${row.CREDIT || ''}</td>
            <td>${row.BALANCE || ''}</td>
        `;
        ledgerBody.appendChild(tr);
    });
}








ledgerBody.addEventListener('click', (e) => {
    const td = e.target.closest('td[data-vtype][data-vno]');
    if (td) {
        const vtype = td.getAttribute('data-vtype');
        const vno = td.getAttribute('data-vno');
        const validVtype=['CR','CP','BR','BP','ADJ','JV'];
        if(validVtype.includes(vtype)){
            vtype != 'JV' ? openDynamicVoucherModal(vtype, vno) : openJvVoucherModal(vno);
        }

        if (vtype == 'PUR' || vtype == 'INV') {
            if(vtype=='PUR'){
                window.open(`/purchase/?bill_no=${vno}`)
            }
            if(vtype=='INV'){
                window.open(`/sale/?bill_no=${vno}`)
            }
            return
        }
    }
})







function openLedgerModal(accCode) {
    document.getElementById('lm_ACC_CODE').focus();
    dateFrom.value = new Date().toISOString().slice(0, 10);
    dateTo.value = new Date().toISOString().slice(0, 10);
    const overlay = document.getElementById('ledgerModalOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.classList.add('active');
        if (accCode) {
            document.getElementById('lm_ACC_CODE').value = accCode;
        }
        // Register with ModalStack so Esc only closes the topmost modal
        if (window.ModalStack) {
            window.ModalStack.push('ledgerModal', () => closeLedgerModal());
        }
    }
}

function closeLedgerModal() {
    const overlay = document.getElementById('ledgerModalOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        if (window.ModalStack) window.ModalStack.pop('ledgerModal');
    }
}

document.getElementById('ledgerModalOverlay')?.addEventListener('click', function (e) {
    if (e.target === this) closeLedgerModal();
});

// Escape is handled globally by ModalStack (global_search_modal.js).
// ModalStack.closeTop() calls closeLedgerModal() via the registered callback.
// Sub-modals (JV, DynamicVoucher) also register themselves, so Esc
// closes only the topmost layer without manual cross-modal checks.
