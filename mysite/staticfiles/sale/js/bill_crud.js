import { openDynamicVoucherModal } from "/static/myledger/js/modals/dynamic_voucher_modal.js";
import { ReceiptModal } from "./waste/recept_modal.js";
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
  old_inv_search,
  discountInput,
  load_bill,
  searchInput,
  receivedAmount,
  deliveryCharges,
  taxPercentInput,
  mscChargesInput,
  remarksInput,
  changeAmount,
  salesMan,
  accCode,
  lastBillAmount,
  loader,
  btnSaveBill,
  btnNewBill,
  directPrinting,
  confirmPrint,
  headerQuoConBy,
  headerQuoConNo,
} from "./dom_elements.js";

// State variables for bill editing
let edit_cart = [];
let Edit_mode = false;
let Edit_voucher_no = null;

let offline_bill_no = 10000
// Payment Mode helper mapping Cash=1, Bank=2, Dual=3 for standard Django Invoice CheckConstraints
function mapPaymentMode(val) {
  if (val === "cash") return 1;
  if (val === "card" || val === "bank") return 2;
  if (val === "dual") return 3;
  return 1;
}

async function save_bill(e) {
  e.preventDefault();
  e.stopImmediatePropagation();

  const discountPercent = Number(discountInput.value || 0);
  const receivedAmountVal = Number(receivedAmount.value || 0);
  if (!receivedAmountVal) return showToast("Please enter received amount");

  const deliveryChargesVal = Number(deliveryCharges?.value || 0);
  const gstPercentVal = Number(taxPercentInput?.value || 0);
  const mscChargesVal = Number(mscChargesInput?.value || 0);
  const remarks = remarksInput.value || "";
  const Payment_method = paymentMode.value || "";
  const card_detail = cardNumber.value;
  const salesManVal = salesMan.value;

  // Enforce require_remarks setting
  const requireRemarks = window.companyConfigurations?.pos?.require_remarks === true;
  if (requireRemarks && !remarks.trim()) {
    showToast('⚠️ Remarks are required before saving the bill', 'error');
    remarksInput?.focus();
    return;
  }

  const cart = getCart();
  if (!cart.length) return showToast("Cart is empty");

  const acc_code = accCode.value || window.getDefaultAccount('cash_client_acc', 112000001);

  // Build payload using payload builder module
  const payload = buildBillPayload({
    cart,
    discountPercent,
    receivedAmount: receivedAmountVal,
    deliveryCharges: deliveryChargesVal,
    gstPercent: gstPercentVal,
    mscCharges: mscChargesVal,
    remarks,
    Payment_method,
    card_detail,
    salesMan: salesManVal,
    acc_code,
    bill_no: hidden_bill_no.value,
    headerQuoConBy: headerQuoConBy.value,
    headerQuoConNo: headerQuoConNo.value,
    mapPaymentMode,
  });

  console.log("offline payload===============", payload);

  // window.DocumentPrinter.printDocument({
  //   bill_no: null,
  //   model_name: 'Invoice',
  //   page_type: "thermal_80",
  //   document_type: "pos_invoice",
  //   data_source: "local",           // "local" | "server"
  //   payload: payload,                 // required when data_source === "local"
  //   allow_multiple_print: false,
  //   copies: 1,
  //   directprint: directPrinting.checked,               // Set to true to print directly without showing preview modal
  // });
  // console.log(
  //   "after DocumentPrinter", payload,
  // )
  // return

  try {
    const isOnlineSoftware = window.companyConfigurations?.general?.online_software !== false;
    if ((!isOnlineSoftware || navigator.onLine ) && true ) {
      const res = await fetch(window.app_constants.save_sale_bills_api || '/sale/api/save_bills/', {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data.success) {
        showToast(`❌ ${data.message || "Error saving bill"}`, 'error');
        return;
      }
      lastBillAmount.textContent = `Last Bill Amount = ${payload.header_net_total.toFixed(3)}`;
      // lastBillAmount.textContent = `Last Bill Amount = 0000.00`;

      const copies = window.companyConfigurations?.general?.multiple_bill_prints || 1;

      window.DocumentPrinter.printDocument({
        bill_no: data.header_voucher_no,
        model_name: 'Invoice',
        page_type: window.companyConfigurations?.pos?.default_page_size || "thermal_80",
        document_type: "pos_invoice",
        data_source: "server",           // "local" | "server"
        payload: null,                 // required when data_source === "local"
        allow_multiple_print: true,
        copies: copies,
        directprint: directPrinting.checked,               // Set to true to print directly without showing preview modal
      });

    } else {
      offline_bill_no += 1;
      const copies = window.companyConfigurations?.general?.multiple_bill_prints || 1;

      await window.DocumentPrinter.printDocument({
        bill_no: offline_bill_no,
        model_name: 'Invoice',
        page_type: window.companyConfigurations?.pos?.default_page_size || "thermal_80",
        document_type: "pos_invoice",
        data_source: "local",           // "local" | "server"
        payload: payload,                 // required when data_source === "local"
        allow_multiple_print: true,
        copies: copies,
        directprint: directPrinting.checked,               // Set to true to print directly without showing preview modal
      });
      throw new Error("Offline mode");
    }
  } catch (err) {
    showToast("Save failed or offline", err);
    await saveBillOffline(payload);
    showToast("Offline: Bill saved locally. It will sync when online.");
    lastBillAmount.textContent = `Last Bill Amount = ${payload.header_net_total.toFixed(3)}`;
    resetUI();
  }



  Edit_mode = false;
  Edit_voucher_no = null;
  edit_cart = [];
  New_bill();
}

function New_bill(e) {
  discountInput.value = 0;
  deliveryCharges.value = 0;
  const defaultGst = window.companyConfigurations?.pos?.total_gst_percent || 0;
  if (taxPercentInput) taxPercentInput.value = defaultGst;
  if (mscChargesInput) mscChargesInput.value = 0;
  receivedAmount.value = 0;
  remarksInput.value = "";
  changeAmount.textContent = "0.00";
  if (hidden_bill_no) hidden_bill_no.value = "";
  if (cardDetails) cardDetails.style.display = "none";
  if (cardNumber) cardNumber.value = "";
  paymentMode.value = "cash";
  searchInput.value = "";
  if (lastBillAmount.textContent.startsWith('Client')) {
    lastBillAmount.innerHTML = 'Last Bill Amount = ' + 0;
  }


  if (headerQuoConBy) headerQuoConBy.value = '';
  if (headerQuoConNo) headerQuoConNo.value = '';

  startNewBill();
}

function old_inv_print_view(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    let query = old_inv_search.value;
    // fetchBill(query);
    // refreshCartUI();

    window.DocumentPrinter.printDocument({
      bill_no: query,
      model_name: 'Invoice',
      page_type: window.companyConfigurations?.pos?.default_page_size || "thermal_80",
      document_type: "pos_invoice",
      data_source: "server",           // "local" | "server"
      // payload: payload,                 // required when data_source === "local"
      allow_multiple_print: true,
      copies: 1,
      directprint: directPrinting.checked,
    });

    old_inv_search.value = "";
    searchInput.focus();
  }
}

function load_prv_bill(load_old_bill = true) {
  if (load_bill) {
    load_bill.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
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

async function fetchBill(voucherNo = null, load_old_bill = false, convertIntoBill = 0) {
  let url;
  if (convertIntoBill && convertIntoBill > 0) {
    url = voucherNo
      ? window.app_constants.get_quotation_bill_api ? window.app_constants.get_quotation_bill_api + `${encodeURIComponent(voucherNo)}` : `/quotation/api/fetch_bill/${encodeURIComponent(voucherNo)}/`
      : window.app_constants.get_quotation_bill_api;
  } else {
    url = voucherNo
      ? window.app_constants.get_sale_bill_api ? window.app_constants.get_sale_bill_api + `${encodeURIComponent(voucherNo)}` : `/sale/api/get_bill/${encodeURIComponent(voucherNo)}/`
      : window.app_constants.get_sale_bill_api;
  }
  // console.log('caled fecthc', url);

  try {
    const res = await fetch(url);
    if (!res.ok) {
      return alert("Network error fetching bill.", "error");
    }
    const data = await res.json();

    if (!data.success) {
      return alert(data.message || "Bill not found", "error");
    }

    if (load_old_bill) {
      console.log(data.data)
      await loadBillIntoCart(data.data);




      const bill = data.data;
      if (bill.header_payment_mode == 1) {
        paymentMode.value = 'cash';
        receivedAmount.value = bill.header_total_paid || 0;
      } else if (bill.header_payment_mode == 2) {
        paymentMode.value = 'card';
        receivedAmount.value = bill.header_total_paid || 0;
      } else if (bill.header_payment_mode == 3) {
        paymentMode.value = 'dual';
        receivedAmount.value = bill.header_cash_paid || 0;
        changeAmount.value = bill.header_card_paid || 0;
      }
      handlePaymentModeChange();
      if (cardNumber) cardNumber.value = bill.header_card_last4 ? `*******${bill.header_card_last4}` : "";

      if (bill.header_acc_code !== 112000001) lastBillAmount.innerHTML = 'Account Code: ' + bill.header_acc_code;

      discountInput.value = bill.header_discount_percent || 0;
      deliveryCharges.value = bill.header_delivery_charges || 0;
      if (bill.header_msc_charges) mscChargesInput.value = bill.header_msc_charges;
      if (bill.header_gst_percent) taxPercentInput.value = bill.header_gst_percent;
      remarksInput.value = bill.header_remarks || "";
      if (hidden_bill_no && convertIntoBill <= 0) hidden_bill_no.value = bill.bill_no;

      if (convertIntoBill && convertIntoBill > 0) {

        if (bill.user) headerQuoConBy.value = bill.user;
        if (bill.bill_no) headerQuoConNo.value = bill.bill_no;
      }

      console.log('called header', headerQuoConBy.value, headerQuoConNo.value)

      Edit_mode = true;
      Edit_voucher_no = bill.voucher_no || bill.bill_no;

      renderCart(getCart());
      refreshCartUI();
    } else {
      const receiptData = buildReceiptData({}, false, data.data);
      call_Receipt_func(receiptData);
    }
  } catch (err) {
    console.error(err);
    alert("Network error fetching bill.", "error");
  }
}





export async function deleteBill(bill_no,pur_inv){
  if(!bill_no) return alert("No bill to delete", "error");
  if(!pur_inv) return alert("No purchase invoice to delete", "error");
    if (confirm("Are you sure you want to delete this bill?")) {
      try {
        
        const res = await fetch(window.app_constants.delete_sale_bill_api ? window.app_constants.delete_sale_bill_api + `${encodeURIComponent(pur_inv)}` + `${encodeURIComponent(bill_no)}` : `/sale/api/delete_sale_bill/${encodeURIComponent(pur_inv)}/${encodeURIComponent(bill_no)}/`);
        if (!res.ok) return alert("Network error deleting bildl", "error");
        const data = await res.json();
        if (!data.success) return alert(data.message);
        alert(data.message, "success");

        New_bill();
      } catch (e) {
        alert(e.message, "error");
      }
    }
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
    items: items.map((i) => ({
      description: i.description,
      qty: i.qty,
      price: i.rate || i.price,
      amount: i.amount,
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

function calculateTotals(items = [], discountPercent = 0, deliveryChargesVal = 0) {
  const total = items.reduce((sum, i) => sum + (i.amount || 0), 0);
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
