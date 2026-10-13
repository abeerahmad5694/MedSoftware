import { openDynamicVoucherModal } from "/static/myledger/js/modals/dynamic_voucher_modal.js";
import { ReceiptModal } from "./waste/recept_modal.js";
import smart_search from "./search_product_modal.js";
import {
  fetchBill,
  save_bill,
  New_bill,
  old_inv_print_view,
  load_prv_bill,
  Edit_mode,
  edit_cart
} from "./bill_crud.js";
import {
  renderCart,
  getCart,
  addToLocalCart,
  deleteCartItem,
  initialize_cart_row_id,
  updateLocalCartItem,
  findCartIndexById,
  removeFromLocalCart,
  clearCart,
  loadBillIntoCart,
  create_unique_row_no,
  saveCart
} from "./cart.js";
import {
  getCookie,
  selectLastRow,
  refreshCartUI,
  showToast,
  resetUI,
  handlePaymentModeChange
} from "./helper_func.js";
import {
  hidden_bill_no,
  paymentMode,
  cardDetails,
  cardNumber,
  barcodeScanCheckbox,
  old_inv_search,
  discountInput,
  load_bill,
  searchInput,
  btnSaveBill,
  btnNewBill,
  multiline,
  deliveryCharges,
  taxPercentInput,
  mscChargesInput,
  receivedAmount,
  remarksInput,
  changeAmount,
  salesMan,
  accCode,
  lastBillAmount,
  loader,
  enterCodeLabel,
  btnConvertToWholesale,
  btnCashPay,
  btnCashReceive,
  priceModeRadios,
  getSelectedRow,
  getAllCartRows,
  getCartRowById,
  btnSearch,
  btnConvertToBill,
  btnDeleteBill
} from "./dom_elements.js";
import {
  saveBillOffline,
  syncoffline_bills,
  searchProductOffline,
  scan_barcode
} from "./indexdb_crud.js";
import { features, get_features } from "./waste/pos_features.js";
import { POS_MAPPING } from "/static/quotation/js/config/constants.js";

let allowSync = true;

document.addEventListener("DOMContentLoaded", async () => {
  await get_features();
  // console.log('adkfjalkjfdlksjfklj/')
  // Load inventory into IndexedDB on load if not present
  // if (window.IndexDBConfig) {
  //   try {
  //     await window.IndexDBConfig.check_and_load_inventory();
  //     window.IndexDBConfig.sync_indexdb('inventory', 'Inventory');
  //   } catch (err) {
  //     console.error("Failed to check or sync inventory database:", err);
  //   }
  // }

  const urlParams = new URLSearchParams(window.location.search);
  const voucherNo = urlParams.get("bill_no");
  // const convertIntoBill = urlParams.get('convertIntoBill')

  console.log('ulparams',urlParams)
  if (voucherNo) {
    console.log('voucher',voucherNo)
    await fetchBill(voucherNo, true);
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  

  if (loader) loader.style.display = "none";
  // if(date) date.value = new Date();

  

  await initialize_cart_row_id();
  const cart = getCart();

  const posConfig = window.companyConfigurations?.pos || {};
  if (posConfig.tax_charges_allowed !== false && taxPercentInput && !parseFloat(taxPercentInput.value)) {
    taxPercentInput.value = posConfig.total_gst_percent || 0;
  }

  Setup_Listeners();
  renderCart(cart);
  refreshCartUI();
  selectLastRow();
  load_prv_bill();
  searchInput.focus();

  window.addEventListener('companyConfigurationsLoaded', (e) => {
    const config = e.detail?.pos || {};
    if (config.tax_charges_allowed !== false && taxPercentInput && !parseFloat(taxPercentInput.value)) {
      taxPercentInput.value = config.total_gst_percent || 0;
    }
    renderCart(getCart());
    refreshCartUI();
  });
});


btnConvertToBill.addEventListener('click',async (e)=>{
  // if(!hidden_bill_no.value) return showToast("HIidedn bill notfoud")
  // console.log('hidden bill no -' , hidden_bill_no.value)
  const old_bill_no = hidden_bill_no.value
  // return;
  if (!old_bill_no ){
    // confirm('Do You Allow To Save Quotation First')
    showToast("Quotation is Saved and Converted to bill")
    const also_convert_into_bill= true
    await save_bill(e ,also_convert_into_bill)
    return 
  }
  else if(old_bill_no>0){
    btnNewBill.click()
    window.location.href = `/sale/?convertIntoBill=${old_bill_no}`
  } 
  else{
    showToast(
      'There is something wrong! Please try again.'
    )
  }
  
  

})





import { deleteBill } from "/static/sale/js/bill_crud.js";


if (btnDeleteBill) {
  btnDeleteBill.addEventListener("click", async (e) => {
    const voucherNo = hidden_bill_no.value;
    const pur_inv = 'Q';
    await deleteBill(voucherNo,pur_inv)
  });
}


function Setup_Listeners() {
  old_inv_search.addEventListener('keydown', old_inv_print_view);
  btnNewBill.addEventListener('click', New_bill);
  btnSaveBill.addEventListener('click', save_bill);
  searchInput.addEventListener('keydown', Search_Input_handler);
  if (discountInput) discountInput.addEventListener('input', Restrictions);

  priceModeRadios.forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const selectedValue = e.target.value;
      const modeId = POS_MAPPING.radioValueToModeId[selectedValue] || 1;
      const modeKey = String(modeId);

      const currentSelectedRow = getSelectedRow();
      if (!currentSelectedRow) return;

      const cartRowId = currentSelectedRow.dataset.rowId;
      const cart = getCart();
      const item = cart.find((i) => i.cart_row_id === cartRowId);

      if (!item) return;

      // Guard against missing prices/discounts
      if (!item.prices || !item.discounts) {
        console.warn("Item missing prices or discounts map:", item);
        return;
      }

      item.packing_mode = modeId;
      item.rate = item.prices[modeKey] ?? 0;
      item.discount_percent_per_item = item.discounts[modeKey] ?? 0;

      const updatedCart = updateLocalCartItem(cartRowId, {
        packing_mode: modeId,
        rate: item.rate,
        discount_percent_per_item: item.discount_percent_per_item
      });

      renderCart(updatedCart);
      refreshCartUI();

      // Re-select updated row
      getAllCartRows()
        .forEach((r) => r.classList.remove("selected-row"));
      const newRow = getCartRowById(cartRowId);
      if (newRow) {
        newRow.classList.add("selected-row");
        newRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  });
}

btnConvertToWholesale.addEventListener('click', (e) => {
  const selectedValue = "wholesale";
  const modeId = POS_MAPPING.radioValueToModeId[selectedValue] || 1;
  console.log('click');

  const cart = getCart();
  cart.forEach((item) => {
    item.packing_mode = modeId;
    item.rate = item.prices[modeId] || 0;
    item.discount_percent_per_item = item.discounts[modeId] || 0;
    updateLocalCartItem(item.cart_row_id, {
      packing_mode: modeId,
      rate: item.rate,
      discount_percent_per_item: item.discount_percent_per_item
    });
  });

  renderCart(getCart());
  refreshCartUI();
});

if (deliveryCharges) deliveryCharges.addEventListener("input", refreshCartUI);
if (taxPercentInput) taxPercentInput.addEventListener("input", refreshCartUI);
if (mscChargesInput) mscChargesInput.addEventListener("input", refreshCartUI);
if (receivedAmount) receivedAmount.addEventListener("input", refreshCartUI);

window.addEventListener("online", () => {
  if (allowSync) {
    syncoffline_bills();
    allowSync = false;
  }
});

if (enterCodeLabel) {
  enterCodeLabel.addEventListener("click", (e) => {
    e.preventDefault();
    if (allowSync) {
      syncoffline_bills();
      allowSync = true;
    }
  });
}

// reset when connection is lost
window.addEventListener("offline", () => {
  allowSync = true;
});

async function searchProduct(query, barcodeScan = null) {
  const matches = await searchProductOffline(query); // always offline first
  if (matches.length > 0) {
    const product = matches[0];
    return { success: true, product: { ...product, weight_total: 1 } };
  }

  // fallback to server if online
  if (navigator.onLine) {
    try {
      
      let url = window.app_constants.sale_add_cart_api ? `${window.app_constants.sale_add_cart_api}?code=${encodeURIComponent(query)}` : `/sale/api/add_cart/?code=${encodeURIComponent(query)}`;
      if (barcodeScan) {
        url = url + `&barcode_scan=${barcodeScan}`;
      }
      const tFetch0 = performance.now();
      const res = await fetch(url);
      const tFetch1 = performance.now();
      console.log(`[searchProduct] Network fetch to backend took: ${(tFetch1 - tFetch0).toFixed(2)} ms`);
      if (!res.ok) {
        return { success: false, message: "Item not found offline or online" };
      }
      return await res.json();
    } catch (err) {
      showToast("Server search failed");
      return { success: false, message: "Item not found offline or online" };
    }
  }

  return { success: false, message: "Item not found offline" };
}

function Restrictions() {
  const discount_percent = parseFloat(discountInput.value) || 0;

  // Read limit from global company configuration (0 = unlimited)
  const posConfig = window.companyConfigurations?.pos || {};
  const maxTotalDiscountPercent = parseFloat(posConfig.max_total_discount_percent) || 0;

  if (maxTotalDiscountPercent > 0 && discount_percent > maxTotalDiscountPercent) {
    showToast(`⚠️ Max total bill discount allowed is ${maxTotalDiscountPercent}%`, 'error');
    discountInput.value = maxTotalDiscountPercent.toFixed(2);
  }

  refreshCartUI();
}

async function Search_Input_handler(evt) {
  if (evt.key === "Delete") {
    const selectedRow = getSelectedRow();
    if (selectedRow) {
      const rowId = selectedRow.dataset.rowId;
      deleteCartItem(rowId);
    }
  }

  if (evt.key === "Tab") {
    evt.preventDefault();
    searchInput.value = "";
    if (btnSearch) btnSearch.click();
  }

  if (evt.key !== "Enter") return;
  const query = searchInput.value.trim();
  if (query.startsWith("++") || query.startsWith("#") || query.startsWith("//")) {
    smart_search(query);
    searchInput.value = "";
    return;
  }

  const shortcuts = ["/", "**", "*", "=", "-", "+"];
  const shortcut = shortcuts.find((s) => query.startsWith(s));

  if (shortcut) {
    const afterShortcut = query.slice(shortcut.length);
    if (!/^-?\d+(\.\d+)?$/.test(afterShortcut)) {
      searchInput.value = "";
      return;
    }

    smart_search(query);
    searchInput.value = "";
    return;
  }

  if (!query) return;

  const tTotalStart = performance.now();
  try {
    const barcodeScan = barcodeScanCheckbox.checked;
    
    const tSearch0 = performance.now();
    const data = await searchProduct(query, barcodeScan);
    const tSearch1 = performance.now();
    console.log(`[Flow] searchProduct took: ${(tSearch1 - tSearch0).toFixed(2)} ms`);

    if (!data.success) {
      showToast(data.message || "Item not found");
      searchInput.value = "";
      return;
    }

    const product = data.product;
    
    const tCartAdd0 = performance.now();
    const cart = addToLocalCart(product);
    const tCartAdd1 = performance.now();
    console.log(`[Flow] addToLocalCart took: ${(tCartAdd1 - tCartAdd0).toFixed(2)} ms`);

    const tRender0 = performance.now();
    renderCart(cart);
    const tRender1 = performance.now();
    console.log(`[Flow] renderCart took: ${(tRender1 - tRender0).toFixed(2)} ms`);

    searchInput.value = "";
    console.log(`[Flow] Total Search -> Cart -> Render flow took: ${(performance.now() - tTotalStart).toFixed(2)} ms`);
  } catch (err) {
    console.error("Error searching product:", err);
    alert("Error searching product");
  }
}

if (btnCashReceive) btnCashReceive.addEventListener("click", () => openDynamicVoucherModal("CR"));
if (btnCashPay) btnCashPay.addEventListener("click", () => openDynamicVoucherModal("CP"));

export {
  btnSaveBill,
  updateLocalCartItem,
  getCart,
  addToLocalCart,
  findCartIndexById,
  removeFromLocalCart,
  deleteCartItem,
  clearCart,
  loadBillIntoCart,
  create_unique_row_no,
  saveCart,
  edit_cart,
  Edit_mode,
};
