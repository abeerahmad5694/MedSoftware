import { POS_MAPPING } from "/static/sale/js/config/constants.js";
import { features } from "./waste/pos_features.js";
import {
  multiline,
  paymentMode,
  receivedAmount,
  deliveryCharges,
  cardNumber,
  cardDetails,
  cartBody,
  itemTotal,
  netTotal,
  discountInput,
  bankAmountInput,
  discountAmount,
  deliveryChargesDisplay,
  changeAmount
} from "./dom_elements.js";
import {
  clearStore,
  getAllRecords,
  putRecordsBatch
} from "/static/myglobal/js/services/local_storage/session_storage_manager.js";

const CART_STORE = "purchasecart";

// In-Memory Optimized Cart Cache and Map for O(1) operations
let cachedCart = [];
const cachedCartMap = new Map();
let countrow = 0;
let isPreloaded = false;

export async function preloadCart() {
  if (isPreloaded) return;
  try {
    const dbCart = await getAllRecords(CART_STORE);
    if (dbCart && dbCart.length > 0) {
      cachedCart = dbCart;
      cachedCartMap.clear();
      cachedCart.forEach((item) => {
        cachedCartMap.set(String(item.cart_row_id), item);
      });
      countrow = cachedCart.length;
    } else {
      // Fallback/Migration from sessionStorage if present
      const sessionData = sessionStorage.getItem("cart");
      if (sessionData) {
        cachedCart = JSON.parse(sessionData) || [];
        cachedCartMap.clear();
        cachedCart.forEach((item) => {
          cachedCartMap.set(String(item.cart_row_id), item);
        });
        countrow = cachedCart.length;
        await putRecordsBatch(CART_STORE, cachedCart);
      }
    }
    isPreloaded = true;
  } catch (err) {
    console.error("Failed to preload cart from IndexedDB:", err);
  }
}

async function initialize_cart_row_id() {
  await preloadCart();
  const cart = getCart();
  if (!cart.length) {
    countrow = 0;
    return;
  }
  countrow = cart.length;
}

function saveCart(cart) {
  cachedCart = cart;
  cachedCartMap.clear();
  cart.forEach((item) => {
    cachedCartMap.set(String(item.cart_row_id), item);
  });
  // Write through to sessionStorage for redundancy
  sessionStorage.setItem("cart", JSON.stringify(cart));
  // Write through to IndexedDB asynchronously in background (extremely fast)
  clearStore(CART_STORE)
    .then(() => putRecordsBatch(CART_STORE, cart))
    .catch(err => console.error("Error saving cart to IndexedDB:", err));
}

function getCart() {
  if (cachedCart && cachedCart.length > 0) return cachedCart;
  // If not preloaded yet, read from sessionStorage as immediate sync fallback
  cachedCart = JSON.parse(sessionStorage.getItem("cart")) || [];
  cachedCartMap.clear();
  cachedCart.forEach((item) => {
    cachedCartMap.set(String(item.cart_row_id), item);
  });
  return cachedCart;
}

function clearCart() {
  cachedCart = [];
  cachedCartMap.clear();
  sessionStorage.removeItem("cart");
  clearStore(CART_STORE).catch(err => console.error("Error clearing cart in IndexedDB:", err));
}

function findCartIndexById(id) {
  const cart = getCart();
  return cart.findIndex((it) => String(it.id) === String(id));
}

function create_unique_row_no() {
  countrow++;
  return `${countrow}`;
}

function addToLocalCart(products) {
  const cart = getCart();
  let uoms = {};
  const list = Array.isArray(products) ? products : [products];

  const selectedRadio = document.querySelector('input[name="price_mode"]:checked')?.value || "base";
  const defaultModeId = String(POS_MAPPING.radioValueToModeId[selectedRadio] || 1);

  // Pre-build index of product IDs to allow O(1) duplicate checks
  const productMap = new Map();
  if (!multiline.checked) {
    cart.forEach((item) => {
      productMap.set(String(item.id), item);
    });
  }

  for (const product of list) {
    const qtyToAdd = Number(product.weight_total ?? 1);
    const productId = product[POS_MAPPING.product.inv_id] || product.inv_id || product.id;

    if (!multiline.checked) {
      const existingItem = productMap.get(String(productId));
      if (existingItem) {
        existingItem.qty += qtyToAdd;
        applyCalculation(existingItem);
        continue;
      }
    }

    const prices = {};
    const discounts = {};
    const qtyFactors = {};

    Object.entries(POS_MAPPING.packingModes).forEach(([modeId, config]) => {
      const key = String(modeId);
      prices[key] = Number(product[config.priceField] || 0);
      discounts[key] = Number(product[config.discField] || 0);
      uoms[key] = product[config.uom] || "";
      qtyFactors[key] = config.qtyFactorField
        ? Number(product[config.qtyFactorField]) || config.defaultFactor
        : config.defaultFactor;
    });

    const initialRate = prices[defaultModeId] || prices["1"] || 0;
    const initialDiscPer = discounts[defaultModeId] || 0;

    // Dynamically build fields based on custom PURCHASE_CART_ROW_FIELDS registry
    const dynamicFields = {};
    if (window.PURCHASE_CART_ROW_FIELDS) {
      for (const [fieldName, fieldConfig] of Object.entries(window.PURCHASE_CART_ROW_FIELDS)) {
        dynamicFields[fieldName] = product[fieldName] !== undefined ? product[fieldName] : (fieldConfig.default ?? "");
      }
    }

    const item = {
      cart_row_id: create_unique_row_no(),
      id: productId,
      product_description: product[POS_MAPPING.product.prod_name] || product.prod_name || product.product_description,
      prod_name_ur: product.prod_name_ur || "",
      qty: qtyToAdd,
      packing_mode: Number(defaultModeId),
      prices,
      discounts,
      qtyFactors,
      uoms,
      rate: initialRate,
      discount_percent_per_item: initialDiscPer,
      discount: (qtyToAdd * initialRate * initialDiscPer) / 100,
      amount: (qtyToAdd * initialRate) - ((qtyToAdd * initialRate * initialDiscPer) / 100),
      prod_categ: product.category || product.prod_categ || "",
      ...dynamicFields
    };

    applyCalculation(item);
    cart.push(item);
    // Add to mapping in case list contains duplicates
    if (!multiline.checked) {
      productMap.set(String(productId), item);
    }
  }

  saveCart(cart);
  return cart;
}

function updateLocalCartItem(cartRowId, changes) {
  const cart = getCart();
  const item = cachedCartMap.get(String(cartRowId));
  if (!item) return cart;

  // Sync general changes and dynamic row inputs
  Object.assign(item, changes);

  applyCalculation(item, changes);
  saveCart(cart);
  return cart;
}

function removeFromLocalCart(cartRowId) {
  const cart = getCart();
  const newCart = cart.filter((it) => String(it.cart_row_id) !== String(cartRowId));
  saveCart(newCart);
  return newCart;
}

export function startNewBill() {
  clearCart();
  countrow = 0;
  renderCart([]);
}

function deleteCartItem(cartRowId) {
  const newCart = removeFromLocalCart(cartRowId);
  renderCart(newCart);
  refreshCartUI();
}

function calculateCartItem({
  qty = 0,
  rate = 0,
  discount = 0,
  discount_percent_per_item = 0
}) {
  qty = Number(qty) || 0;
  rate = Number(rate) || 0;

  const baseTotal = qty * rate;

  let finalDiscount = Number(discount) || 0;
  let finalDiscountPercent = Number(discount_percent_per_item) || 0;

  if (finalDiscountPercent > 0) {
    finalDiscount = (baseTotal * finalDiscountPercent) / 100;
  } else if (finalDiscount > 0) {
    finalDiscountPercent = (finalDiscount / baseTotal) * 100;
  }

  return {
    qty,
    rate,
    baseTotal: Number(baseTotal.toFixed(2)),
    discount: Number(finalDiscount.toFixed(2)),
    discount_percent_per_item: Number(finalDiscountPercent.toFixed(2)),
    amount: Number((baseTotal - finalDiscount).toFixed(2))
  };
}

function applyCalculation(item, overrides = {}) {
  const result = calculateCartItem({
    qty: overrides.qty ?? item.qty,
    rate: overrides.rate ?? item.rate,
    discount: overrides.discount ?? item.discount,
    discount_percent_per_item: overrides.discount_percent_per_item ?? item.discount_percent_per_item,
  });

  Object.assign(item, result);
  return item;
}

async function loadBillIntoCart(bill) {
  clearCart();
  console.log('calling')

  const items = bill.items || [];
  const cart = await Promise.all(items.map(async (item) => {
    const invId = Number(item.inv_id || item.id);
    let originalItem = null;
    if (invId && window.IndexDBConfig && typeof window.IndexDBConfig.get_record === "function") {
      try {
        originalItem = await window.IndexDBConfig.get_record("inventory", invId);
      } catch (err) {
        console.warn("Could not load original item from IndexedDB for inv_id:", invId, err);
      }
    }

    const prices = {};
    const discounts = {};
    const qtyFactors = {};
    const uoms = {};

    Object.entries(POS_MAPPING.packingModes).forEach(([modeId, config]) => {
      const key = String(modeId);
      if (originalItem) {
        prices[key] = Number(originalItem[config.priceField] || 0);
        discounts[key] = Number(originalItem[config.discField] || 0);
        uoms[key] = originalItem[config.uom] || "";
        qtyFactors[key] = config.qtyFactorField
          ? Number(originalItem[config.qtyFactorField]) || config.defaultFactor
          : config.defaultFactor;
      } else {
        prices[key] = Number(item[config.priceField] || 0);
        discounts[key] = Number(item[config.discField] || 0);
        uoms[key] = item[config.uom] || "";
        qtyFactors[key] = config.qtyFactorField
          ? Number(item[config.qtyFactorField]) || config.defaultFactor
          : config.defaultFactor;
      }
    });

    const packingMode = Number(item.packing_mode || 1);
    const itemRate = Number(item.rate || item.price || 0);

    // Keep the original invoice price for the current packing mode
    prices[String(packingMode)] = itemRate;

    const discountAmt = features.pos_discount_per_item
      ? Number(item.discount || item.row_discount_amount || 0)
      : 0;
    const discountPct = item.row_discount_percent || 0;

    // Load custom dynamic row fields from the bill item
    const dynamicFields = {};
    if (window.PURCHASE_CART_ROW_FIELDS) {
      for (const [fieldName, fieldConfig] of Object.entries(window.PURCHASE_CART_ROW_FIELDS)) {
        dynamicFields[fieldName] = item[fieldName] !== undefined ? item[fieldName] : (fieldConfig.default ?? "");
      }
    }

    return {
      cart_row_id: create_unique_row_no(),
      id: invId || item.id,
      product_description: item.description || item.prod_name || (originalItem ? (originalItem.prod_name || originalItem.prod_desc) : ""),
      qty: Number(item.qty),
      packing_mode: packingMode,
      prices,
      discounts,
      qtyFactors,
      uoms,
      rate: itemRate,
      discount: discountAmt,
      discount_percent_per_item: discountPct,
      amount: Number(item.amount || item.row_net_total || 0),
      prod_categ: item.prod_categ || (originalItem ? originalItem.category : ""),
      row_old_total_base_qty : Number(item.qty) * Number(item.pack_qty || 1),
      ...dynamicFields
    };
  }));

  saveCart(cart);
}



















// _______________________ Render Cart (Optimized for 100x Speed) _________________________
function renderCart(cartItems) {
  const cart = cartItems ?? getCart();

  if (!cartBody) return;

  // Build the thead dynamically based on custom row fields configured in the registry
  const thead = document.querySelector("#cart-form table thead");
  if (thead && window.PURCHASE_CART_ROW_FIELDS) {
    let dynamicHeaders = "";
    for (const [fieldName, fieldConfig] of Object.entries(window.PURCHASE_CART_ROW_FIELDS)) {
      dynamicHeaders += `<th style="width: ${fieldConfig.width || '100px'}">${fieldConfig.title || fieldName}</th>`;
    }
    thead.innerHTML = `
      <tr>
        
        <th style="width: 350px">Item Name</th>
        <th style="width: 40px">Qty /</th>
        <th style="width: 40px">PMode</th>
        <th style="width: 120px">Rate //</th>
        <th style="width: 50px;" >Disc-Per *</th>
        <th style="width: 100px">Disc-Amt</th>
        <th style="width: 130px">Total</th>
        ${dynamicHeaders}
        <th style="width: 10px">▲</th>
      </tr>
    `;
  }

  if (!cart || cart.length === 0) {
    const totalColumns = 8 + (window.PURCHASE_CART_ROW_FIELDS ? Object.keys(window.PURCHASE_CART_ROW_FIELDS).length : 0);
    cartBody.innerHTML = `
      <tr id="empty-row">
        <td colspan="${totalColumns}" style="text-align:center; color:#999; padding:20px; font-size:20px;">
          No items added
        </td>
      </tr>`;
    if (itemTotal) itemTotal.textContent = "0.00";
    if (netTotal) netTotal.textContent = "0.00";
    return;
  }

  let totalAmount = 0;
  let htmlAccumulator = "";

  cart.forEach((item) => {
    const amount = Number(item.amount) || 0;
    totalAmount += amount;

    // Build packing mode options dynamically based on window.PURCHASE_CART_PACKING_MODES
    const packingModes = window.PURCHASE_CART_PACKING_MODES || {
      "1": "Retail",
      "2": "Carton",
      "3": "Dozen",
      "4": "WSale"
    };
    let packingOptions = "";
    for (const [value, label] of Object.entries(packingModes)) {
      packingOptions += `<option value="${value}" ${Number(item.packing_mode) === Number(value) ? 'selected' : ''}>${label}</option>`;
    }
    const packingModeDropdown = `
      <select class="cart-input packing-mode-select" style="padding: 2px 4px; font-size: 13px; width: 100%;">
        ${packingOptions}
      </select>
    `;

    // Render dynamic inputs based on window.PURCHASE_CART_ROW_FIELDS registry
    let dynamicCells = "";
    if (window.PURCHASE_CART_ROW_FIELDS) {
      for (const [fieldName, fieldConfig] of Object.entries(window.PURCHASE_CART_ROW_FIELDS)) {
        const fieldValue = item[fieldName] !== undefined && item[fieldName] !== null ? item[fieldName] : (fieldConfig.default ?? "");
        dynamicCells += `
          <td style="width: ${fieldConfig.width || '100px'};">
            <input type="${fieldConfig.type}" placeholder = '0' value="${fieldValue}" class="${fieldConfig.input_class || 'cart-input'}" data-field-name="${fieldName}" style="width: 80%;" />
          </td>
        `;
      }
    }

    const row = `
      <tr class="cart-item-row" data-row-id="${item.cart_row_id}">
        
        <td class="desc-cell" style="width: 200px;">
          <input type="text" value="${item.product_description} (${item.id})" readonly class="input-flat" style="width: 100%;" />
          <input type="hidden" value="${item.id}" name="item_id" />
        </td>
        <td style="width: 80px;">
          <input type="number" value="${item.qty}" step="0.5" min="0" class="cart-input qty-input" style="width: 100%;" />
        </td>
        <td style="width: 80px;">
          ${packingModeDropdown}
        </td>
        <td style="width: 100px;">
          <input type="number" value="${item.rate}" step="1" min="0" class="cart-input rate-input" style="width: 100%;" />
        </td>
        <td>
          <input type="number" value="${item.discount_percent_per_item || 0}" step="0.5" min="0" class="cart-input discount_percent_per_item-input" style="width: 100%;" />
        </td>
        <td>
          <input type="number" value="${item.discount || 0}" step="0.5" min="0" class="cart-input discount_per_item-input" style="width: 100%;" />
        </td>
        <td style="width: 100px;">
          <input type="number" value="${amount.toFixed(2)}" readonly step="0.01" class="cart-input amount-input" style="width: 100%;" />
        </td>

        ${dynamicCells}
        <td style="width: 20px;">
          <button type="button" class="btn small remove-item-btn" data-row-id="${item.cart_row_id}">×</button>
        </td>


      </tr>`;

    htmlAccumulator += row;
  });

  cartBody.innerHTML = htmlAccumulator;

  if (itemTotal) itemTotal.textContent = totalAmount.toFixed(2);
  if (netTotal) netTotal.textContent = totalAmount.toFixed(2);

  bindCartEvents();
  refreshCartUI();
  selectLastRow();
}

function selectedRow(row) {
  row.addEventListener("click", () => {
    document
      .querySelectorAll(".cart-item-row")
      .forEach((r) => r.classList.remove("selected-row"));
    row.classList.add("selected-row");
  });
}

// ______________________ Event Binding (Optimized using Delegation) ____________________________
let listenersInitialized = false;

function bindCartEvents() {
  if (!cartBody) return;

  if (!listenersInitialized) {
    cartBody.addEventListener("focusout", (e) => {
      const classes = ["qty-input", "rate-input", "discount_per_item-input", "discount_percent_per_item-input", "packing-mode-select"];
      const isDynamicField = e.target.dataset.fieldName !== undefined;
      if (classes.some(cls => e.target.classList.contains(cls)) || isDynamicField) {
        handleCartUpdate.call(e.target);
      }
    });


    if (discountAmount) {
          discountAmount.addEventListener("focusout", () => {
            const cart = getCart();
            let total = 0;
            cart.forEach((item) => { total += item.amount || 0; });
            const typedAmount = parseFloat(discountAmount.value) || 0;
            const newPercent = total > 0 ? (typedAmount / total) * 100 : 0;
            if (discountInput) discountInput.value = newPercent.toFixed(2);
            refreshCartUI();
          });
        }
        

    cartBody.addEventListener("click", (e) => {
      const removeBtn = e.target.closest(".remove-item-btn");
      if (removeBtn) {
        deleteCartItem(removeBtn.dataset.rowId);
        return;
      }

      const row = e.target.closest(".cart-item-row");
      if (row) {
        document.querySelectorAll(".cart-item-row").forEach((r) => r.classList.remove("selected-row"));
        row.classList.add("selected-row");
      }
    });

    listenersInitialized = true;
  }
}

// _________________________ Handle Live Cart Updates _________________________________
function handleCartUpdate() {
  const row = this.closest("tr");
  if (!row) return;

  const cartRowId = row.dataset.rowId;
  const item = cachedCartMap.get(String(cartRowId));
  if (!item) return;

  // Handle dynamic field update if this input corresponds to a dynamic field
  if (this.dataset.fieldName) {
    item[this.dataset.fieldName] = this.value;
  }

  const packingMode = parseInt(row.querySelector(".packing-mode-select")?.value) || 1;
  let rate = Number(row.querySelector(".rate-input").value) || 0;
  let discountPercent = Number(item.discount_percent_per_item) || 0;

  if (this.classList.contains("packing-mode-select")) {
    const modeKey = String(packingMode);
    rate = item.prices?.[modeKey] ?? rate;
    discountPercent = item.discounts?.[modeKey] ?? discountPercent;

    row.querySelector(".rate-input").value = rate;
    const discPctEl = row.querySelector(".discount_percent_per_item-input");
    if (discPctEl) discPctEl.value = discountPercent;
  }

  if (this.classList.contains("rate-input")) {
    if (!item.prices) item.prices = {};
    item.prices[String(packingMode)] = rate;
  }

  if (this.classList.contains("discount_percent_per_item-input")) {
    if (!item.discounts) item.discounts = {};
    const typedDiscPercent = Number(row.querySelector(".discount_percent_per_item-input").value) || 0;
    item.discounts[String(packingMode)] = typedDiscPercent;
    discountPercent = typedDiscPercent;
  }

  const changes = {
    qty: Number(row.querySelector(".qty-input").value) || 0,
    rate: rate,
    packing_mode: packingMode,
    discount_percent_per_item: discountPercent
  };

  if (features.pos_discount_per_item) {
    if (this.classList.contains("discount_per_item-input")) {
      changes.discount = Number(row.querySelector(".discount_per_item-input").value) || 0;
      changes.discount_percent_per_item = 0;
    } else if (this.classList.contains("discount_percent_per_item-input")) {
      changes.discount_percent_per_item = discountPercent;
      changes.discount = 0;
    }
  }

  // Populate dynamic fields into the updates
  if (window.PURCHASE_CART_ROW_FIELDS) {
    for (const fieldName of Object.keys(window.PURCHASE_CART_ROW_FIELDS)) {
      const inputEl = row.querySelector(`[data-field-name="${fieldName}"]`);
      if (inputEl) {
        changes[fieldName] = inputEl.value;
      }
    }
  }

  const updatedCart = updateLocalCartItem(cartRowId, changes);
  const updated = cachedCartMap.get(String(cartRowId));

  if (updated) {
    row.querySelector(".amount-input").value = updated.amount.toFixed(2);
    if (features.pos_discount_per_item) {
      const discAmtEl = row.querySelector(".discount_per_item-input");
      const discPctEl = row.querySelector(".discount_percent_per_item-input");
      if (discAmtEl) discAmtEl.value = updated.discount.toFixed(2);
      if (discPctEl) discPctEl.value = updated.discount_percent_per_item.toFixed(2);
    }
  }

  refreshCartUI();
}

// _________________________ Select Last Row _________________________________
function selectLastRow() {
  const rows = document.querySelectorAll(".cart-item-row");
  if (rows.length === 0) return;

  rows.forEach((r) => r.classList.remove("selected-row"));

  const lastRow = rows[rows.length - 1];
  lastRow.classList.add("selected-row");
  lastRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ______________________ Refresh Cart UI _____________________________
function refreshCartUI() {
  let total = 0;

  // Optimized O(N) memory loop instead of querying inputs from the DOM
  const cart = getCart();
  cart.forEach((item) => {
    total += item.amount || 0;
  });

  const discountPercent = parseFloat(discountInput?.value) || 0;
  const deliveryChargesVal = parseFloat(deliveryCharges?.value) || 0;

  const receivedInput = receivedAmount;
  let receivedAmountVal = receivedInput ? parseFloat(receivedInput.value) || 0 : 0;

  const calculatedDiscountAmount = (total * discountPercent) / 100;
  const calculatedNetTotal = total - calculatedDiscountAmount + deliveryChargesVal;

  if (paymentMode.value == 'cash' && receivedInput && receivedAmountVal < calculatedNetTotal && receivedAmountVal > 0) {
    receivedAmountVal = 0;
    receivedInput.value = calculatedNetTotal.toFixed(2);
    receivedAmountVal = parseFloat(receivedInput.value) || 0;
  }
  if (paymentMode.value == 'dual' && receivedInput && receivedInput.value > 0) {
    const bankAmountVal = calculatedNetTotal - receivedInput.value;
    if (bankAmountInput) {
      bankAmountInput.value = bankAmountVal.toFixed(2);
    }
    receivedAmountVal = parseFloat(receivedInput.value) || 0;
  }
  const balance = calculatedNetTotal - receivedAmountVal;

  if (paymentMode && paymentMode.value === "card" && receivedAmountVal > 0 && receivedInput) {
    receivedAmountVal = 0;
    receivedInput.value = calculatedNetTotal.toFixed(2);
    receivedAmountVal = parseFloat(receivedInput.value) || 0;
  }

  if (itemTotal) itemTotal.textContent = total.toFixed(2);
  // if (discountAmount) discountAmount.textContent = calculatedDiscountAmount.toFixed(2);
  if (discountAmount) discountAmount.value = calculatedDiscountAmount.toFixed(2);
  if (deliveryChargesDisplay) deliveryChargesDisplay.tefxtContent = deliveryChargesVal.toFixed(2);
  if (netTotal) netTotal.textContent = calculatedNetTotal.toFixed(2);
  if (changeAmount) changeAmount.textContent = balance.toFixed(2);
}

export {
  renderCart,
  selectedRow,
  bindCartEvents,
  handleCartUpdate,
  selectLastRow,
  refreshCartUI,
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
  initialize_cart_row_id,
  countrow,
};
