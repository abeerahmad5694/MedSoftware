import { openDynamicVoucherModal } from "/static/myledger/js/modals/dynamic_voucher_modal.js";
import { deleteBill } from "/static/sale/js/bill_crud.js";

import { buildBillPayload } from "./payload.js";
import {
  getCart,
  loadBillIntoCart,
  startNewBill,
  renderCart,
  refreshCartUI
} from "./cart.js";
import { saveBillOffline } from "./indexdb_crud.js";
import {
  getCookie,
  showToast,
  resetUI,
  handlePaymentModeChange
} from "./helper_func.js";
import {
  hidden_bill_no,
  paymentMode,
  cardDetails,
  cardNumber,
  itemTotal,
  netTotal,
  bankAmount,
  bankAmountInput,
  receivedAmountLabel,
  changeAmountLabel,
  old_inv_search,
  discountInput,
  discountAmount,
  load_bill,
  searchInput,
  receivedAmount,
  deliveryCharges,
  remarksInput,
  changeAmount,
  salesMan,
  accCode,
  lastBillAmount,
  deliveryChargesDisplay,
  loader,
  btnSaveBill,
  btnNewBill,
  supplierInvNo,
  supplierInvDate,
  ourRef,
  ourRefDate,
  deliveredBy,
  freightAmount,
  labourAmount,
  unloadAmount, 
  directPrinting,
  confirmPrint,
  cashAmount,
  date,
  unloadAccCode,
  freightAccCode,
  labourAccCode,
  billTypeRadioButton,
  purchaseReturnRadio,
  btnDeleteBill,
} from "./dom_elements.js";

// State variables for bill editing
let edit_cart = [];
let Edit_mode = false;
let Edit_voucher_no = null;

// Payment Mode helper mapping Cash=1, Bank=2, Dual=3 for standard Django Invoice CheckConstraints
function mapPaymentMode(val) {
  // if (val === "112000001") return 1;
  // if (val === "card" || val === "bank") return 2;
  // if (val === "dual") return 3;
  return parseInt(val);
}

async function save_bill(event) {
  event.preventDefault();
  event.stopImmediatePropagation();

  const discountPercent = Number(discountInput.value || 0);
  const receivedAmountVal = Number(receivedAmount.value || 0);
  if (!receivedAmountVal) return showToast("Please enter received amount");

  const deliveryChargesVal = Number(deliveryCharges.value || 0);
  const remarks = remarksInput.value || "";
  const Payment_method = paymentMode.value || "112000001";
  const card_detail = cardNumber.value;
  const salesManVal = salesMan.value;


  const header_supl_inv_no = supplierInvNo.value || 0
  const header_supl_inv_date = supplierInvDate.value || null
  const header_our_ref = ourRef.value || 0
  const header_our_ref_date = ourRefDate.value || null
  const header_delivery_person = deliveredBy.value || null

  const header_freight_amount = freightAmount.value || 0
  const header_labour_amount = labourAmount.value || 0
  const header_unload_amount = unloadAmount.value || 0
  const header_date = date.value || null

  const header_unload_acc_code = unloadAccCode.value || 0
  const header_freight_acc_code = freightAccCode.value || 0
  const header_labour_acc_code = labourAccCode.value || 0


  if(!purchaseReturnRadio.checked && (header_freight_amount < 0 || header_labour_amount < 0 || header_unload_amount < 0 )){
    return alert('In Purchase Negative Amount Not Allowed')
  }


  const cart = getCart();
  if (!cart.length) return showToast("Cart is empty");

  const acc_code = accCode.value || 112000001;

  // Build payload using payload builder module
  const result = buildBillPayload({
    cart,
    discountPercent,
    receivedAmount: receivedAmountVal,
    deliveryCharges: deliveryChargesVal,
    remarks,
    Payment_method,
    card_detail,
    salesMan: salesManVal,
    acc_code,

    header_date,

    header_supl_inv_no,
    header_supl_inv_date,
    header_our_ref,
    header_our_ref_date,
    header_delivery_person,
    header_freight_amount,
    header_labour_amount,
    header_unload_amount,
    header_freight_acc_code,
    header_labour_acc_code,
    header_unload_acc_code,

    bill_no: hidden_bill_no.value,
    billTypeRadioButton,
    // mapPaymentMode,
  });

  if (!result.success){
    alert(result.message);
    return;
  }
  const payload = result.payload;

  // console.log(payload);
  
  // console.log('kdsjkjklj')
  const purPageSize = window.companyConfigurations?.purchase?.default_page_size || "thermal_80";
  try {
    const isOnlineSoftware = window.companyConfigurations?.general?.online_software !== false;
    if (!isOnlineSoftware || navigator.onLine) {
      console.log('onnline')
      const res = await fetch(window.app_constants.save_purchase_bills_api || '/purchase/api/save_bills/', {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data.success) return alert(data.message || "Error saving bill");
      lastBillAmount.textContent = `Last Bill Amount = ${payload.header_net_total}`;


      
      console.log(purPageSize);
      const copies = window.companyConfigurations?.general?.multiple_bill_prints || 1;
      console.log('copies', copies)
      window.DocumentPrinter.printDocument({
        bill_no: data.bill_no,
        model_name: 'Purchase',
        page_type: purPageSize.toLowerCase(),
        document_type: "purchase_invoice",
        data_source: "server",           // "local" | "server"
        payload: payload,                 // required when data_source === "local"
        allow_multiple_print: true,
        copies: copies,
        directprint: directPrinting.checked,           
      });

    } else {

      //const purPageSize = window.companyConfigurations?.purchase?.default_page_size || "thermal_80";
      console.log(purPageSize);
      const copies = window.companyConfigurations?.general?.copies || 1;

      window.DocumentPrinter.printDocument({
        bill_no: null,
        model_name: 'Purchase',
        page_type: purPageSize.toLowerCase(),
        document_type: "purchase_invoice",
        data_source: "local",           // "local" | "server"
        payload: payload,                 // required when data_source === "local"
        allow_multiple_print: true,
        copies: copies,
        directprint: directPrinting.checked,           
      });
      throw new Error("Offline mode");
    }
  } catch (error) {
    console.log('offline saved')
    showToast("Save failed or offline", error);
    await saveBillOffline(payload);
    showToast("Offline: Bill saved locally. It will sync when online.");
    // lastBillAmount.textContent = `Last Bill Amount = ${payload.header_net_total}`;
    resetUI();
  }

  Edit_mode = false;
  Edit_voucher_no = null;
  edit_cart = [];
  New_bill();
}

function New_bill(event) {
  discountInput.value = 0;
  deliveryCharges.value = 0;
  receivedAmount.value = 0;
  remarksInput.value = "";
  changeAmount.textContent = "0.00";
  if (hidden_bill_no) hidden_bill_no.value = "";
  if (cardDetails) cardDetails.style.display = "none";
  if (cardNumber) cardNumber.value = "";
  paymentMode.value = window.getDefaultAccount('default_cash_acc', 110000001);
  // console.log
  searchInput.value = "";
  lastBillAmount.innerHTML = 'Last Bill Amount = ' + 0;

  document.getElementById("bill-header-form")?.reset();

  // Reset default account codes dynamically from Default Accounts configuration
  if (typeof window.getDefaultAccount === "function") {
    const freightCodeInput = document.getElementById("freight_acc_code");
    const labourCodeInput = document.getElementById("labour_acc_code");
    const unloadCodeInput = document.getElementById("unload_acc_code");

    if (freightCodeInput) freightCodeInput.value = window.getDefaultAccount('freight_payable_acc', 231000124);
    if (labourCodeInput) labourCodeInput.value = window.getDefaultAccount('labour_payable_acc', 231000123);
    if (unloadCodeInput) unloadCodeInput.value = window.getDefaultAccount('unload_payable_acc', 231000125);
  }

  startNewBill();
}

function old_inv_print_view(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    let query = old_inv_search.value;
    // fetchBill(query);
    // refreshCartUI();
    window.DocumentPrinter.printDocument({
        bill_no: query,
        model_name: 'Invoice',
        page_type: "thermal_80",
        document_type: "pos_invoice",
        data_source: "server",           // "local" | "server"
        // payload: payload,                 // required when data_source === "local"
        allow_multiple_print: true,
        copies: 2,
        directprint: directPrinting.checked,           
      });
    old_inv_search.value = "";
    searchInput.focus();
  }
}



function load_prv_bill(load_old_bill = true) {
  if (load_bill) {
    load_bill.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        let query = load_bill.value;
        console.log(`${query} this is value`);
        await fetchBill(query, load_old_bill);
        refreshCartUI();
        load_bill.value = "";
        searchInput.focus();
      }
    });
  }
}





async function fetchBill(voucherNo = null, load_old_bill = false) {
  const url = voucherNo
    ? window.app_constants.get_purchase_bill_api 
      ? window.app_constants.get_purchase_bill_api + `${encodeURIComponent(voucherNo)}` 
      : `/purchase/api/get_bill/${encodeURIComponent(voucherNo)}/`
    : window.app_constants.get_purchase_bill_api;

  if (loader) loader.style.display = 'flex';

  try {
    const res = await fetch(url);
    if (!res.ok) {
      if (loader) loader.style.display = 'none';
      return alert("Network error fetching bill.", "error");
    }
    const data = await res.json();

    if (!data.success) {
      if (loader) loader.style.display = 'none';
      return alert(data.message || "Bill not found", "error");
    }
    
    const bill = data.data;
    console.log('bill', bill);

    if (load_old_bill) {
      await loadBillIntoCart(bill);

      // Supplier / Account fields
      if (accCode) accCode.value = bill.header_acc_code || '';
      if (document.getElementById('supplier-code')) document.getElementById('supplier-code').value = bill.header_acc_code || '';
      if (document.getElementById('supplier-name')) document.getElementById('supplier-name').value = bill.header_acc_code || ''; // change if you have supplier name field

      // Invoice details card
      if (supplierInvNo) supplierInvNo.value = bill.header_supl_inv_no || '';
      if (supplierInvDate) supplierInvDate.value = bill.header_supl_inv_date ? formatDateForInput(bill.header_supl_inv_date) : '';
      if (ourRef) ourRef.value = bill.header_our_ref || '';
      if (ourRefDate) ourRefDate.value = bill.header_our_ref_date ? formatDateForInput(bill.header_our_ref_date) : '';
      if (deliveredBy) deliveredBy.value = bill.header_delivery_person || '';
      if (freightAmount) freightAmount.value = bill.header_freight_amount ?? '0.00';
      if (labourAmount) labourAmount.value = bill.header_labour_amount ?? '0.00';
      if (unloadAmount) unloadAmount.value = bill.header_unload_amount ?? '0.00';

      // Invoice summary card
      if (old_inv_search) old_inv_search.value = bill.bill_no || '';
      if (date) date.value = bill.date ? formatDateForInput(bill.date) : '';

      // Hidden fields
      if (hidden_bill_no) hidden_bill_no.value = bill.bill_no || '';
      if (load_bill) load_bill.value = bill.bill_no || '';

      // Totals section
      if (discountInput) discountInput.value = bill.header_discount_percent ?? 0;
      if (discountAmount) discountAmount.textContent = (parseFloat(bill.header_discount_amount) ?? 0).toFixed(2);
      if (deliveryCharges) deliveryCharges.value = bill.header_delivery_charges ?? 0;
      if (deliveryChargesDisplay) deliveryChargesDisplay.textContent = (parseFloat(bill.header_delivery_charges) ?? 0).toFixed(2);
      if (itemTotal) itemTotal.textContent = (parseFloat(bill.header_item_total) ?? 0).toFixed(2);
      if (netTotal) netTotal.textContent = (parseFloat(bill.header_net_total) ?? 0).toFixed(2);

      // Payment section

      if (paymentMode) {
        paymentMode.value = bill.header_payment_mode || '112000001'; // ACC_CODE directly
      }

      // if (paymentMode) {
        // Adjust these values to match your select options
        // if (bill.header_payment_mode == 1) paymentMode.value = 'cash';
        // else if (bill.header_payment_mode == 2) paymentMode.value = 'card';
        // else if (bill.header_payment_mode == 3) paymentMode.value = 'dual';
        // else paymentMode.value = 'cash';
      // }
      if (receivedAmount) receivedAmount.value = parseFloat(bill.header_total_paid) ?? 0;
      if (changeAmount) changeAmount.textContent = (parseFloat(bill.header_change_amount) ?? 0).toFixed(2);
      if (cashAmount) cashAmount.querySelector('input').value = parseFloat(bill.header_cash_paid) ?? 0;
      if (bankAmount) bankAmountInput.value = parseFloat(bill.header_bank_paid) ?? 0;
      if (cardNumber) cardNumber.value = bill.header_card_last4 ? `**** **** **** ${bill.header_card_last4}` : "";

      // Remarks + others
      if (remarksInput) remarksInput.value = bill.header_remarks || "";
      if (salesMan) salesMan.value = bill.salesman || "";

      // // Extra info display
      // if (lastBillAmount && bill.header_acc_code && bill.header_acc_code != 112000001) {
      //   lastBillAmount.style.display = 'block';
      //   lastBillAmount.innerHTML = 'Account Code: ' + bill.header_acc_code;
      // }

      // Set edit mode flags
      Edit_mode = true;
      Edit_voucher_no = bill.bill_no;

      // Trigger UI updates
      // if (typeof handlePaymentModeChange === 'function') handlePaymentModeChange();
      renderCart(getCart());
      refreshCartUI();
      if (typeof updateTotals === 'function') updateTotals();

    } else {
      const receiptData = buildReceiptData({}, false, bill);
      call_Receipt_func(receiptData);
    }
  } catch (error) {
    console.error(error);
    alert("Network error fetching bill.", "error");
  } finally {
    if (loader) loader.style.display = 'none';
  }
}






if (btnDeleteBill) {
  btnDeleteBill.addEventListener("click", async (e) => {
    const voucherNo = hidden_bill_no.value;
    const pur_inv = 'P';
    await deleteBill(voucherNo,pur_inv)
  });
}








// Helper: convert MM-DD-YYYY to YYYY-MM-DD for input[type=date]
function formatDateForInput(dateStr) {
  if (!dateStr) return '';
  // Handles MM-DD-YYYY from strftime('%m-%d-%Y')
  const parts = dateStr.split('-');
  if (parts.length === 3 && parts[2].length === 4) {
    const [mm, dd, yyyy] = parts;
    return `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
  }
  // If already YYYY-MM-DD or ISO
  return dateStr.substring(0, 10);
}









function buildReceiptData(payload = {}, offline = false, serverData = {}) {
  const items = offline ? payload.items || [] : serverData.items || [];

  const discountPercent = offline
    ? payload.discountPercent || 0
    : serverData.discountPercent || 0;
  const deliveryChargesVal = offline
    ? payload.deliveryCharges || 0
    : serverData.delivery_charges || 0;

  const {
    total,
    discount,
    net_total: calc_net_total,
  } = calculateTotals(items, discountPercent, deliveryChargesVal);

  let net_total = offline
    ? calc_net_total
    : Number(serverData.net_total) || calc_net_total;
  let change_amount = offline ? null : serverData.change_amount || 0;

  return {
    items: items.map((item) => ({
      description: item.description,
      qty: item.qty,
      price: item.rate || item.price,
      amount: item.amount,
    })),
    shop: offline
      ? null
      : serverData.show_header
        ? serverData.company_name
        : "",
    net_total,
    date: offline
      ? new Date().toLocaleString()
      : serverData.date || new Date().toLocaleString(),
    voucher_no: offline ? `${Date.now()}` : serverData.voucher_no || "N/A",
    total,
    discountPercent,
    discount,
    delivery_charges: deliveryChargesVal,
    received_amount: offline
      ? payload.receivedAmount || 0
      : serverData.received_amount || 0,
    change_amount,
    payment_mode: offline
      ? payload.Payment_method || "cash"
      : serverData.payment_mode || "cash",
    remarks: offline ? payload.remarks || "" : serverData.remarks || "",
    header_text: offline ? null : serverData.header_text || "",
    footer_text: offline ? null : serverData.footer_text || "",
    logo: offline ? null : serverData.logo || null,
  };
}

// Replace i with item in calculateTotals
function calculateTotals(items = [], discountPercent = 0, deliveryChargesVal = 0) {
  const total = items.reduce((sum, item) => sum + (item.amount || 0), 0);
  const discount = Number(total * (discountPercent / 100));
  const net_total = total - discount + deliveryChargesVal;
  return { total, discount, net_total };
}

function call_Receipt_func(receiptData) {
  if (directPrinting && directPrinting.checked) {
    ReceiptModal.print(receiptData);
  } else {
    ReceiptModal.open(receiptData);
    const printBtn = confirmPrint;
    if (printBtn) {
      const clonedPrintBtn = printBtn.cloneNode(true);
      printBtn.replaceWith(clonedPrintBtn);
      clonedPrintBtn.onclick = () => ReceiptModal.print(receiptData);
    }
  }
}

export {
  save_bill,
  New_bill,
  old_inv_print_view,
  load_prv_bill,
  fetchBill,
  buildReceiptData,
  calculateTotals,
  call_Receipt_func,
  mapPaymentMode,
  edit_cart,
  Edit_mode,
  Edit_voucher_no,
};
