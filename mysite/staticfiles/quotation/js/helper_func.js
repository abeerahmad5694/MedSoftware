import {
  updateLocalCartItem,
  findCartIndexById,
  getCart,
  removeFromLocalCart,
  deleteCartItem,
  clearCart,
  renderCart,
  selectedRow,
  bindCartEvents,
  handleCartUpdate,
  selectLastRow,
  refreshCartUI
} from "./cart.js";

import { ReceiptModal } from "./waste/recept_modal.js";
import { features, get_features } from "./waste/pos_features.js";
import {
  fetchBill,
  buildReceiptData,
  calculateTotals,
  call_Receipt_func
} from "./bill_crud.js";

import {
  paymentMode,
  cardDetails,
  cardNumber,
  searchInput,
  deliveryCharges,
  old_inv_search,
  load_bill,
  discountInput,
  receivedAmount,
  lastBillAmount,
  cashAmount,
  bankAmount,
  receivedAmountLabel,
  changeAmountLabel,
  zoomInBtn,
  zoomOutBtn,
  getAllCartRows,
  btnNewBill,
  btnConvertToBill,
  btnSaveBill,
  btnConvertToWholesale,
  btnSelectClient,
  multiline,
  directPrinting, 
  barcodeScanCheckbox,
} from "./dom_elements.js";

let is_discount_per_item = true;

// _______________________ Zoom Controller ________________
let zoom = 1;
const body = document.body;
if (zoomInBtn) {
  zoomInBtn.addEventListener("click", () => {
    body.style.zoom = zoom += 0.1;
  });
}

if (zoomOutBtn) {
  zoomOutBtn.addEventListener("click", () => {
    body.style.zoom = zoom = Math.max(0.5, zoom - 0.1);
  });
}

// _______________________ Key Events Control ____________________
document.addEventListener("keydown", function (e) {
  if (e.ctrlKey && e.key.toLowerCase() === "d") {
    e.preventDefault(); 
    if (deliveryCharges) deliveryCharges.focus();
  }

  if (e.ctrlKey && e.key.toLowerCase() === "i") {
    e.preventDefault();
    if (old_inv_search) {
      old_inv_search.scrollIntoView({ behavior: "smooth", block: "center" });
      old_inv_search.focus();
    }
  }

  if (e.ctrlKey && e.key.toLowerCase() === "l") {
    e.preventDefault();
    if (load_bill) {
      load_bill.scrollIntoView({ behavior: "smooth", block: "center" });
      load_bill.focus();
    }
  }


  if (e.altKey && e.key.toLowerCase() === "n") {
    e.preventDefault();
    e.stopPropagation();
    if (btnNewBill) btnNewBill.click();
  }
  
  if (e.ctrlKey && e.key.toLowerCase() === "q") {
    e.preventDefault();
    if (btnConvertToBill) btnConvertToBill.click();
  }
  if (e.ctrlKey && e.key.toLowerCase() === "s") {
    e.preventDefault();
    if (btnSaveBill) btnSaveBill.click();
  }
  if (e.altKey && e.key.toLowerCase() === "w") {
    e.preventDefault();
    if(btnConvertToWholesale) btnConvertToWholesale.click();
  }
  if (e.altKey && e.key.toLowerCase() === "c") {
    e.preventDefault();
    if(btnSelectClient) btnSelectClient.click();
  }
  if(e.altKey && e.key.toLowerCase() === "m"){
    e.preventDefault();
    if(multiline) multiline.click();
  }
  if(e.altKey && e.key.toLowerCase() === "d"){
    e.preventDefault();
    if(directPrinting) directPrinting.click();
  }
  if(e.altKey && e.key.toLowerCase() === "b"){
    e.preventDefault();
    if(barcodeScanCheckbox) barcodeScanCheckbox.click();
  }
  else if (e.altKey) {
    let modeValue = null;

    switch (e.key.toLowerCase()) {
      case "1":
      case "b":
        modeValue = "base";
        break;
      case "2":
      case "w":
        modeValue = "wholesale";
        break;
      case "3":
      case "c":
        modeValue = "carton";
        break;
      case "4":
      case "d":
        modeValue = "dzn";
        break;
    }

    if (modeValue) {
      e.preventDefault();
      
      // Find matching radio input by value
      const targetRadio = document.querySelector(`input[name="price_mode"][value="${modeValue}"]`);
      
      if (targetRadio && !targetRadio.checked) {
        targetRadio.checked = true;
        // This fires your existing priceModeRadios event listener
        targetRadio.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  }


    

  // Escape to search
  if (e.key === "Escape") {
    e.preventDefault();
    if (searchInput) {
      searchInput.focus();
      searchInput.value = "";
    }
  }

  // Row navigation keys
  const rows = getAllCartRows();
  if (rows.length === 0) return;

  let currentIndex = Array.from(rows).findIndex((r) =>
    r.classList.contains("selected-row")
  );

  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();

    if (currentIndex !== -1) {
      rows[currentIndex].classList.remove("selected-row");
    }

    if (e.key === "ArrowDown") {
      currentIndex = (currentIndex + 1) % rows.length;
    } else if (e.key === "ArrowUp") {
      currentIndex = (currentIndex - 1 + rows.length) % rows.length;
    }

    rows[currentIndex].classList.add("selected-row");
    rows[currentIndex].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});

if (lastBillAmount) {
  lastBillAmount.addEventListener("click", () => {
    fetchBill();
  });
}

// _______________________ Get CSRF Cookie _____________________________
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ________________________ Payment Mode UI Box Listener _____________________
export function handlePaymentModeChange() {
  if (paymentMode.value === "card") {
    if (receivedAmountLabel) receivedAmountLabel.textContent = "Received Card Amount (+)";
    if (changeAmountLabel) changeAmountLabel.textContent = 'Change Amount';
    if (cardDetails) cardDetails.style.display = "block";
    if (cardNumber) cardNumber.focus();
  }

  else if (paymentMode.value === "dual") {
    if (receivedAmountLabel) receivedAmountLabel.textContent =
      "Enter Cash Amount. Remaining will take as Card (+)";
    if (receivedAmountLabel) receivedAmountLabel.style.color = '#d56262';
    if (changeAmountLabel) changeAmountLabel.textContent = 'Taken as Bank Amount';
    if (cardDetails) cardDetails.style.display = "block";
  }

  else {
    if (receivedAmountLabel) receivedAmountLabel.textContent = "Received Cash Amount (+)";
    if (changeAmountLabel) changeAmountLabel.textContent = 'Change Amount';
    if (cardDetails) cardDetails.style.display = "none";
    if (cardNumber) cardNumber.value = "";
  }
}

if (paymentMode) {
  paymentMode.addEventListener("change", handlePaymentModeChange);
}

// ___________________ Toast Alerts ___________________
function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.textContent = msg;
  toast.style.position = "fixed";
  toast.style.bottom = "20px";
  toast.style.right = "20px";
  toast.style.padding = "10px 16px";
  toast.style.background =
    type === "success" ? "#4CAF50" : type === "error" ? "#f44336" : "#2196F3";
  toast.style.color = "#fff";
  toast.style.borderRadius = "6px";
  toast.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
  toast.style.zIndex = "9999";
  toast.style.opacity = "0";
  toast.style.transition = "opacity 0.3s ease";
  document.body.appendChild(toast);
  setTimeout(() => (toast.style.opacity = "1"), 50);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}

function resetUI() {
  if (discountInput) discountInput.value = 0;
  if (deliveryCharges) deliveryCharges.value = 0;
  if (receivedAmount) receivedAmount.value = 0;

  clearCart();
  renderCart();
  refreshCartUI();

  if (cardDetails) cardDetails.style.display = "none";
  if (cardNumber) cardNumber.value = "";
  if (paymentMode) paymentMode.value = "cash";
}

export {
  renderCart,
  selectedRow,
  getCookie,
  bindCartEvents,
  handleCartUpdate,
  selectLastRow,
  refreshCartUI,
  fetchBill,
  buildReceiptData,
  showToast,
  resetUI,
  calculateTotals,
  call_Receipt_func,
};
