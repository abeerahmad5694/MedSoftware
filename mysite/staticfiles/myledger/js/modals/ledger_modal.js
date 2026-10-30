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
        searchFields: ['ACC_CODE', 'ACC_NAME' ],
        displayColumns: [
            { key: 'ACC_CODE', header: 'Code', width: '20%' },
            { key: 'ACC_NAME', header: 'Account Name', width: '30%' },
            { key: 'ADDRESS', header: 'Address', width: '30%' },
            { key: 'PHONE_OFF', header: 'Phone Number', width: '20%' },
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
            <td hidden>${row.AMOUNT || ''}</td>
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


// ============================================================
// Print Ledger  — opens a tiny print window (most reliable)
// ============================================================
document.getElementById('lm_printBtn')?.addEventListener('click', () => {

    // 1. Collect header info
    const accCode  = document.getElementById('lm_ACC_CODE')?.value  || '';
    const accName  = document.getElementById('lm_ACC_NAME')?.value  || '';
    const address  = document.getElementById('lm_ADDRESS')?.value   || '';
    const phone    = document.getElementById('lm_PHONE_OFF')?.value || document.getElementById('lm_MOBILE_NO')?.value || '';
    const dateFrom = document.getElementById('lm_DATE_FROM')?.value || '';
    const dateTo   = document.getElementById('lm_DATE_TO')?.value   || '';

    // 2. Company info
    const cfg      = window.companyConfigurations || {};
    const firmName = cfg.company_name || cfg.name || '';
    const logoSrc  = cfg.logo || '';

    // 3. Totals from footer
    const drVal  = document.querySelector('.dr-val')?.textContent  || '0.00';
    const crVal  = document.querySelector('.cr-val')?.textContent  || '0.00';
    const balVal = document.querySelector('.bal-val')?.textContent || '0.00';

    // 4. Clone visible table rows (respects active filter)
    let rowsHtml = '';
    document.querySelectorAll('#lm_ledger-body tr').forEach(row => {
        if (row.style.display === 'none') return;
        rowsHtml += row.outerHTML;
    });

    if (!rowsHtml) return alert('No ledger data to print. Please generate the ledger first.');

    // 5. Build complete HTML for print window
    const logoHtml = logoSrc ? `<img src="${logoSrc}" style="max-height:60px;">` : '';

    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Ledger — ${accName}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #000; padding: 16px; }

    .header { display: flex; align-items: center; gap: 16px; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 10px; }
    .header img { max-height: 60px; }
    .firm-name { font-size: 18px; font-weight: bold; }

    .client-info { margin-bottom: 12px; }
    .client-info table { border-collapse: collapse; }
    .client-info td { padding: 2px 10px 2px 0; vertical-align: top; }
    .client-info td:first-child { font-weight: bold; color: #444; width: 70px; }

    table.ledger { width: 100%; border-collapse: collapse; font-size: 10px; }
    table.ledger th, table.ledger td { border: 1px solid #bbb; padding: 3px 6px; }
    table.ledger th { background: #eee; font-weight: bold; }
    table.ledger td:nth-child(5),
    table.ledger td:nth-child(6),
    table.ledger td:nth-child(7),
    table.ledger td:nth-child(8) { text-align: right; }

    .summary-row td { border-top: 2px solid #000; background: #f5f5f5; font-weight: bold; }
    .summary-row td:nth-child(2),
    .summary-row td:nth-child(3),
    .summary-row td:nth-child(4) { text-align: right; }

    @media print {
      body { padding: 8px; }
    }
  </style>
</head>
<body>

  <div class="header">
    ${logoHtml}
    <div class="firm-name">${firmName}</div>
  </div>

  <div class="client-info">
    <table>
      <tr><td>Account:</td><td>${accCode} — ${accName}</td></tr>
      ${address ? `<tr><td>Address:</td><td>${address}</td></tr>` : ''}
      ${phone   ? `<tr><td>Phone:</td><td>${phone}</td></tr>`     : ''}
      <tr><td>Period:</td><td>${dateFrom} &rarr; ${dateTo}</td></tr>
    </table>
  </div>

  <table class="ledger">
    <thead>
      <tr>
        <th>Type</th><th>Date</th><th>Voucher No</th>
        <th>Description</th><th>Amount</th>
        <th>Debit</th><th>Credit</th><th>Balance</th>
      </tr>
    </thead>
    <tbody>${rowsHtml}</tbody>
    <tfoot>
      <tr class="summary-row">
        <td colspan="5">Total</td>
        <td>${drVal}</td>
        <td>${crVal}</td>
        <td>${balVal}</td>
      </tr>
    </tfoot>
  </table>

  <script>window.onload = function(){ window.print(); window.close(); }<\/script>
</body>
</html>`;

    const win = window.open('', '_blank', 'width=900,height=700');
    win.document.write(html);
    win.document.close();
});
