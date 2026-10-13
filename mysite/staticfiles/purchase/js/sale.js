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
  date
} from "./dom_elements.js";
import {
  saveBillOffline,
  syncoffline_bills,
  searchProductOffline,
  scan_barcode
} from "./indexdb_crud.js";
import { features, get_features } from "./waste/pos_features.js";
import { POS_MAPPING } from "/static/sale/js/config/constants.js";
import { get_all_banks } from "/static/myglobal/js/apis/get_all_banks.js";

let allowSync = true;




async function loadBanks() {
    const banks = await get_all_banks();
    if (!banks || !paymentMode) return alert('No Bank Found');

    paymentMode.innerHTML =  `<option value="${window.getDefaultAccount('default_cash_acc', 110000001)}" selected>Cash</option>`;

    banks.forEach(bank => {
        const option = document.createElement('option');
        option.value = bank.ACC_CODE;
        option.textContent = bank.ACC_NAME;
        paymentMode.appendChild(option);
    });
}



document.addEventListener("DOMContentLoaded", async () => {
  await get_features();
  
  await loadBanks()

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
  if (voucherNo) {
    await fetchBill(voucherNo, true);
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  if (loader) loader.style.display = "none";

  if(date) date.value = new Date().toISOString().split('T')[0]
  await initialize_cart_row_id();
  const cart = getCart();

  // Apply Purchase Configuration toggles
  const purConfig = window.companyConfigurations?.purchase || {};
  
  // 1. Charge row visibility
  const freightRow = document.getElementById("freight-charges-row");
  const labourRow = document.getElementById("labour-charges-row");
  const unloadRow = document.getElementById("unload-charges-row");

  if (freightRow && purConfig.freight_charges_allowed === false) {
    freightRow.style.display = "none";
  }
  if (labourRow && purConfig.labour_charges_allowed === false) {
    labourRow.style.display = "none";
  }
  if (unloadRow && purConfig.unload_charges_allowed === false) {
    unloadRow.style.display = "none";
  }

  // 2. Direct / Silent Printing toggle default
  const directPrintCheckbox = document.getElementById("direct-printing");
  if (directPrintCheckbox && typeof purConfig.default_direct_print_checked === "boolean") {
    directPrintCheckbox.checked = purConfig.default_direct_print_checked;
  }

  // 3. Dynamic Default Account Codes (Freight, Labour, Unload)
  const freightCodeInput = document.getElementById("freight_acc_code");
  const labourCodeInput = document.getElementById("labour_acc_code");
  const unloadCodeInput = document.getElementById("unload_acc_code");

  if (freightCodeInput && typeof window.getDefaultAccount === "function") {
    freightCodeInput.value = window.getDefaultAccount('freight_payable_acc', 231000124);
  }
  if (labourCodeInput && typeof window.getDefaultAccount === "function") {
    labourCodeInput.value = window.getDefaultAccount('labour_payable_acc', 231000123);
  }
  if (unloadCodeInput && typeof window.getDefaultAccount === "function") {
    unloadCodeInput.value = window.getDefaultAccount('unload_payable_acc', 231000125);
  }

  Setup_Listeners();
  renderCart(cart);
  refreshCartUI();
  selectLastRow();
  load_prv_bill();
  searchInput.focus();
});

function Setup_Listeners() {
  old_inv_search.addEventListener('keydown', old_inv_print_view);
  btnNewBill.addEventListener('click', New_bill);
  btnSaveBill.addEventListener('click', save_bill);
  searchInput.addEventListener('keydown', Search_Input_handler);
  discountInput.addEventListener('input', Restrictions);

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

btnConvertToWholesale?.addEventListener('click', (e) => {
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
      console.log("barcodeScan", barcodeScan);
      let url = window.app_constants.sale_add_cart_api ? `${window.app_constants.sale_add_cart_api}?code=${encodeURIComponent(query)}` : `/sale/api/add_cart/?code=${encodeURIComponent(query)}`;
      if (barcodeScan) {
        url = url + `&barcode_scan=${barcodeScan}`;
      }
      const res = await fetch(url);
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
  if (discount_percent > features.pos_disc_flat_limit) {
    alert(`Max discount allowed is ${features.pos_disc_flat_limit}%`);
    discountInput.value = "";
    return;
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

  try {
    const barcodeScan = barcodeScanCheckbox.checked;
    const data = await searchProduct(query, barcodeScan);
    if (!data.success) {
      showToast(data.message || "Item not found");
      searchInput.value = "";
      return;
    }

    const product = data.product;
    const cart = addToLocalCart(product);
    renderCart(cart);
    searchInput.value = "";
  } catch (err) {
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
