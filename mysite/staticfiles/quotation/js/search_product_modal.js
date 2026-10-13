
import {
  renderCart,
  handleCartUpdate,
  refreshCartUI,
  addToLocalCart,
  updateLocalCartItem
} from "./cart.js";

import { fetchBill } from "./bill_crud.js";
import { features } from "./waste/pos_features.js";
import { paymentMode, netTotal, btnSaveBill, btnNewBill } from "./dom_elements.js";


// document.addEventListener("DOMContentLoaded", () => {
//   const productSearch = new GlobalSearchModal({
//     overlaySelector: "#product-modal-overlay",
//     searchInputSelector: "#modal-search-input",
//     resultBodySelector: "#modal-results",
//     paginationSelector: "#modal-pagination",
//     closeBtnSelector: "#modal-close-btn",
//     listUrl: "/sale/product-list/", // Django view
//     searchUrl: "/sale/search/products/", // Django view
//     columns: [
//       { field: "id", label: "ID" },
//       { field: "product_description", label: "Account Name" },
//       { field: "category", label: "Category" },
//       { field: "barcode", label: "Barcode" },
//       { field: "retail_price", label: "Price" },
//     ],
//     pageSize: 15,
//     onPick: (item) => {
      
//       const query = String(item.id)|| String(item.barcode);
      
//       const url = `/sale/add_cart/?code=${encodeURIComponent(query)}`;
//       fetch(url)
//         .then((res) => res.json())
//         .then((data) => {
//           if (data.success == true) {
//             const cart = addToLocalCart(data.product);
//             renderCart(cart);
//           } else {
//             alert("Error while adding product else ");
//           }
//         })
//         .catch((err) => {
//           alert("Error while adding product catch");
//         });
//     },
//   });

//   document
//     .querySelector("#btn-search")
//     .addEventListener("click", () => productSearch.open());
// });

// function for smart search like / to add qty or * to add rate

function smart_search(query) {
  if (!query) return;

  // --- helpers ---
  const parseNum = (str) => parseFloat(str) || 0;
  const el = (sel) => document.querySelector(sel);
  const refresh = () => refreshCartUI();
  const updateInput = (selector, value, cb) => {
    const input = el(selector);
    if (!input) return false;
    input.value = value;
    cb?.call(input);
    return true;
  };


  if (query.startsWith("//")) {
    const rate = parseNum(query.slice(2));
    updateInput(".selected-row .rate-input", rate, handleCartUpdate);
    return;
  }

  if(query.startsWith("*") && !query.startsWith("**")) {
    const posConfig = window.companyConfigurations?.pos || {};
    console.log('pos',posConfig)
    const rowDiscAllowed = posConfig.row_discount_allowed || false;
    if(!rowDiscAllowed) return
    console.log('running')
    let discount_percent_per_item = parseFloat(query.slice(1));
    
    const current_discount = updateInput(
      ".selected-row .discount_percent_per_item-input",
      discount_percent_per_item,handleCartUpdate
    );

    return;
    // current_discount.value = discount_percent_per_item.toFixed(2)

  }

  // --- quantity update (/10 = set qty=10) ---
  if (query.startsWith("/")) {
    const qty = parseNum(query.slice(1));
    updateInput(".selected-row .qty-input", qty, handleCartUpdate);
    return;
  }

  // --- item rate update (*120 = rate=120) ---
  

  // --- discount percent (**10 = discount 10%) ---
  if (query.startsWith("**")) {
    const discount = parseNum(query.slice(2));
    const posConfig = window.companyConfigurations?.pos || {};
    const maxRowDisc = parseFloat(posConfig.max_row_discount_percent) || 0;
    if (maxRowDisc > 0 && parseFloat(discount) > maxRowDisc) {
      showToast(`⚠️ Max row discount allowed is ${maxRowDisc}%`, 'error');
      return;
    }
    updateInput(".discount-row .discount-input", discount, refresh);
    return;
  }

  // --- discount amount (-100 = discount Rs.100) ---
  if (query.startsWith("-")) {
    const total = [...document.querySelectorAll(".amount-input")].reduce(
      (sum, el) => sum + (parseNum(el.value) || 0),
      0
    );

    const discountAmt = parseNum(query.slice(1));
    const percent = total ? (discountAmt / total) * 100 : 0;

    updateInput(".discount-row .discount-input", percent.toFixed(2), refresh);

    const discountEl = el("#discount-amount");
    if (discountEl) discountEl.textContent = discountAmt.toFixed(2);

    refresh();
    return;
  }

  // --- received amount from net total (++) ---
  if (query.startsWith("++")) {
    const paymentModeValue = paymentMode ? paymentMode.value : "";
    if (paymentModeValue == 'dual') {
      return alert('For Dual Payments Enter the Amount of Cash manually using (+) amount ! and the remaining will taken as bank');
    }
    // const netTotalVal = parseNum(netTotal?.textContent.trim());
    // if (updateInput(".payment-row .received-input", netTotalVal.toFixed(2))) {
      btnSaveBill?.click();
      // btnNewBill?.click();
      refresh();
    // }
    return;
  }

  // --- manual received amount (+500 = set 500) ---
  if (query.startsWith("+")) {
    const amount = parseNum(query.slice(1));
    updateInput(".payment-row .received-input", amount, refresh);
    btnSaveBill?.click();
    btnNewBill?.click();
    return;
  }

  // --- set total amount (=500 = recalc qty according to amount) ---
  if (query.startsWith("=")) {
    const rowRate = el(".selected-row .rate-input");
    const rowQty = el(".selected-row .qty-input");
    const rowAmount = el(".selected-row .amount-input");
    if (!rowRate || !rowQty || !rowAmount) return;

    const amount = parseFloat(query.slice(1));
    const qty = rowRate.value ? amount / parseFloat(rowRate.value) : 0;

    rowAmount.value = parseInt(amount.toFixed(2));
    rowQty.value = qty.toFixed(6);
    handleCartUpdate.call(rowAmount)
    refresh();
  }


  if (query.startsWith('#')){
    const vch_no =query.slice(1)
    fetchBill(vch_no)
    refresh();  
  }
}


export default smart_search;
