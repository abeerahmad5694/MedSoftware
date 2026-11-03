import { POS_MAPPING, applyRistrictionsInPurchase } from "/static/sale/js/config/constants.js";
// import removed
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

const main_serial_field = 'serial_no'
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


// =============================================================================
// SERIAL TRACKING CONFIG & HELPERS
// =============================================================================
function ensureSerialStyles() {
  if (document.getElementById("serial-cart-styles")) return;
  const style = document.createElement("style");
  style.id = "serial-cart-styles";
  style.textContent = `
    /* Parent Row Styling */
    .cart-item-row.serial-parent-row {
      background-color: #EFF6FF !important;
      font-weight: 600;
      border-bottom: none !important;
    }
    .cart-item-row.serial-parent-row td {
      background-color: #EFF6FF !important;
      border-bottom: 1px solid #DBEAFE !important;
      font-weight: 600;
      padding-top: 6px;
      padding-bottom: 6px;
    }
    .cart-item-row.serial-parent-row input.input-flat {
      background-color: transparent !important;
      font-weight: 600;
      color: #1E3A8A !important;
    }

    /* Nested Table Row: Attached with No Gap */
    .serial-nested-row td {
      padding: 0 !important;
      border-top: none !important;
      background-color: transparent !important;
    }

    /* Serial Child Container: 92% centered with slight left indent, rounded bottom corners */
    .serial-child-container {
      width: 92%;
      margin: 0 auto;
      margin-left: 4%;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-top: 0;
      border-radius: 0 0 8px 8px;
      padding: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
      box-sizing: border-box;
    }

    /* Serial Sub Table */
    .serial-sub-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }

    /* Serial Header Row: Background #E2E8F0, text #475569, 11px uppercase */
    .serial-sub-table thead tr {
      background-color: #E2E8F0 !important;
      height: 32px;
    }
    .serial-sub-table th {
      user-select: none;
      font-weight: 700;
      color: #475569 !important;
      font-size: 11px !important;
      text-transform: uppercase !important;
      letter-spacing: 0.04em !important;
      padding: 6px 8px !important;
      border-bottom: 1px solid #CBD5E1 !important;
      background-color: #E2E8F0 !important;
      vertical-align: middle;
    }

    /* Serial Inner Rows: 36px height, zebra striping with light colors only */
    .serial-sub-table tbody tr.serial-child-row {
      height: 36px;
      border-bottom: 1px solid #F1F5F9;
      transition: background-color 0.12s ease;
    }
    .serial-sub-table tbody tr.serial-child-row:nth-child(odd) {
      background-color: #FFFFFF !important;
    }
    .serial-sub-table tbody tr.serial-child-row:nth-child(even) {
      background-color: #EEF2FF !important; /* light bluish gray */
    }
    .serial-sub-table tbody tr.serial-child-row:hover {
      background-color: #E0E7FF !important; /* soft pastel hover */
    }
    .serial-sub-table tbody tr.serial-child-row.active-serial-row {
      background-color: #DBEAFE !important;
    }
    .serial-sub-table tbody tr.serial-child-row td {
      height: 36px;
      padding: 2px 6px;
      vertical-align: middle;
    }

    /* Serial Child Inputs */
    .serial-child-input {
      height: 26px;
      padding: 2px 6px;
      font-size: 11px;
      width: 100%;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      background: #FFFFFF;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
      box-sizing: border-box;
      outline: none;
    }
    .serial-child-input:hover {
      border-color: #94A3B8;
    }
    .serial-child-input:focus {
      border-color: #2563EB !important;
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25) !important;
      background: #FFFFFF !important;
    }

    /* Action Buttons in Serial Row */
    .serial-row-actions {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
    }
    .btn-serial-action {
      width: 24px;
      height: 24px;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      font-size: 11px;
      border: 1px solid transparent;
      cursor: pointer;
      background: transparent;
      transition: all 0.15s ease-in-out;
      outline: none;
      color: inherit;
    }
    .btn-serial-action:hover,
    .btn-serial-action:focus,
    .btn-serial-action:focus-visible {
      transform: translateY(-1px);
      outline: none;
    }
    .btn-serial-action.copy-serial-btn {
      color: #2563EB;
      background: #EFF6FF;
      border-color: #BFDBFE;
    }
    .btn-serial-action.copy-serial-btn:hover,
    .btn-serial-action.copy-serial-btn:focus,
    .btn-serial-action.copy-serial-btn:focus-visible {
      background: #2563EB;
      color: #FFFFFF;
      border-color: #1D4ED8;
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.35);
    }
    .btn-serial-action.add-serial-child-btn {
      color: #16A34A;
      background: #F0FDF4;
      border-color: #BBF7D0;
    }
    .btn-serial-action.add-serial-child-btn:hover,
    .btn-serial-action.add-serial-child-btn:focus,
    .btn-serial-action.add-serial-child-btn:focus-visible {
      background: #16A34A;
      color: #FFFFFF;
      border-color: #15803D;
      box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.35);
    }
    .btn-serial-action.remove-serial-btn {
      color: #DC2626;
      background: #FEF2F2;
      border-color: #FECACA;
    }
    .btn-serial-action.remove-serial-btn:hover,
    .btn-serial-action.remove-serial-btn:focus,
    .btn-serial-action.remove-serial-btn:focus-visible {
      background: #DC2626;
      color: #FFFFFF;
      border-color: #B91C1C;
      box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.35);
    }
    .add-serial-btn:hover,
    .add-serial-btn:focus,
    .add-serial-btn:focus-visible {
      background: #1D4ED8 !important;
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.35) !important;
      outline: none !important;
      transform: translateY(-1px);
    }







        /* Group 0 - Green */
    tr.cart-item-row.serial-parent-row.serial-group-2 td {
      background-color: #7ea978bd !important;
    }
    tr.serial-nested-row.serial-group-2 td {
      background-color: #7ea978bd !important;
    }
    tr.serial-nested-row.serial-group-2 .serial-child-container {
      background-color: #7ea978bd !important;
    }

    /* Group 1 - Yellow */
    tr.cart-item-row.serial-parent-row.serial-group-1 td {
      background-color: #FFFBEB !important;
    }
    tr.serial-nested-row.serial-group-1 td {
      background-color: #FFFBEB !important;
    }
    tr.serial-nested-row.serial-group-1 .serial-child-container {
      background-color: #e9e1c1ff !important;
    }

    /* Group 2 - Purple */
    tr.cart-item-row.serial-parent-row.serial-group-0 td {
      background-color: #d0bedbff !important;
    }
    tr.serial-nested-row.serial-group-0 td {
      background-color: #d0bedbff !important;
    }
    tr.serial-nested-row.serial-group-0 .serial-child-container {
      background-color: #c7b4d4ff !important;
    }

    /* Group 3 - Indigo */
    tr.cart-item-row.serial-parent-row.serial-group-3 td {
      background-color: #EEF2FF !important;
    }
    tr.serial-nested-row.serial-group-3 td {
      background-color: #EEF2FF !important;
    }
    tr.serial-nested-row.serial-group-3 .serial-child-container {
      background-color: #EEF2FF !important;
    }










    /* === GROUP WRAPPER - COMPLETE BLOCK BACKGROUND === */
    .serial-group-0 .cart-item-row.serial-parent-row,
    .serial-group-0 .cart-item-row.serial-parent-row td,
    .serial-group-0 .serial-nested-row td {
      background-color: #7ea978bd !important; /* Light Blue Group */
    }
    .serial-group-0 .serial-child-container {
      background-color: #7ea978bd !important;
      border-color: #BFDBFE !important;
    }
    .serial-group-1 .cart-item-row.serial-parent-row,
    .serial-group-1 .cart-item-row.serial-parent-row td,
    .serial-group-1 .serial-nested-row td {
      background-color: #FFFBEB !important; /* Light Yellow Group */
    }
    .serial-group-1 .serial-child-container {
      background-color: #e9e1c1ff !important;
      border-color: #FDE68A !important;
    }
    .serial-group-2 .cart-item-row.serial-parent-row,
    .serial-group-2 .cart-item-row.serial-parent-row td,
    .serial-group-2 .serial-nested-row td {
      background-color: #F0FDF4 !important; /* Light Green Group */
    }
    .serial-group-2 .serial-child-container {
      background-color: #c7b4d4ff !important;
      border-color: #BBF7D0 !important;
    }
    /* Loop back - 3 colors repeat */
    .serial-group-3 .cart-item-row.serial-parent-row,
    .serial-group-3 .cart-item-row.serial-parent-row td,
    .serial-group-3 .serial-nested-row td {
      background-color: #EEF2FF !important; /* Light Indigo Group */
    }
    .serial-group-3 .serial-child-container {
      background-color: #EEF2FF !important;
      border-color: #C7D2FE !important;
    }
    /* Parent row styling - no gap */
    .cart-item-row.serial-parent-row {
      font-weight: 600;
      border-bottom: none !important;
    }
    .cart-item-row.serial-parent-row td {
      font-weight: 700;
      padding-top: 10px;
      padding-bottom: 10px;
      border-bottom: none !important;
    }
    /* Child container - NOW 100% WIDTH - NO GAP - COMPLETE BACKGROUND */
    .serial-nested-row td {
      padding: 0 !important;
      border-top: none !important;
    }
    .serial-child-container {
      width: 100% !important;
      margin: 0 !important;
      border: none !important;
      border-top: 1px dashed #CBD5E1 !important;
      border-radius: 0 !important;
      padding: 8px 12px 12px 12px !important;
      box-shadow: none !important;
    }
    /* Inner serial table - white for clarity */
    .serial-sub-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      background: #FFFFFF;
      border-radius: 6px;
      overflow: hidden;
      border: 1px solid #E2E8F0;
    }
    .serial-sub-table thead tr {
      background: #F8FAFC !important;
      height: 32px;
    }
    .serial-sub-table th {
      background: #F8FAFC !important;
      color: #475569 !important;
      font-size: 11px !important;
      text-transform: uppercase;
      padding: 6px 8px !important;
    }
    /* Zebra inside white table */
    .serial-sub-table tbody tr.serial-child-row {
      height: 36px;
      border-bottom: 1px solid #F1F5F9;
    }
    .serial-sub-table tbody tr.serial-child-row:nth-child(odd) {
      background: #FFFFFF !important;
    }
    .serial-sub-table tbody tr.serial-child-row:nth-child(even) {
      background: #F8FAFC !important;
    }
    .serial-sub-table tbody tr.serial-child-row:hover {
      background: #E0E7FF !important;
    }
    /* Keep your existing inputs / buttons styles as is ... */
    .serial-child-input { height: 26px; padding: 2px 6px; font-size: 11px; width: 100%; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFF; }
    .serial-row-actions { display: inline-flex; gap: 3px; }
    .btn-serial-action { width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; border-radius: 4px; font-size: 11px; border: 1px solid transparent; cursor: pointer; }
  




  `;
  document.head.appendChild(style);
}

function getSerialFieldsConfigForCategory(catId) {
  const cfg = window.companyConfigurations?.inventory?.serial_fields_config || {};
  let fields = (catId && cfg[String(catId)]) ? cfg[String(catId)] : (cfg["0"] || []);
  if (!Array.isArray(fields) || fields.length === 0) {
    fields = [
      { field_name: "serial_no", label: "Serial / IMEI / Chassis", is_required: true, sort_order: 1 },
      { field_name: "serial_no2", label: "IMEI 2 / Engine No", is_required: false, sort_order: 2 },
      { field_name: "color", label: "Color", is_required: false, sort_order: 3 },
      { field_name: "processor", label: "Processor", is_required: false, sort_order: 4 },
      { field_name: "ram", label: "RAM", is_required: false, sort_order: 5 },
      { field_name: "storage", label: "Storage", is_required: false, sort_order: 6 },
      { field_name: "condition", label: "Condition", is_required: true, sort_order: 7 },
      { field_name: "model_year", label: "Model Year", is_required: false, sort_order: 8 },
      { field_name: "warranty_end", label: "Warranty End", is_required: false, sort_order: 9 },
    ];
  }
  let filtered = fields
    .filter(f => f.field_name !== "cost" && f.field_name !== "individual_cost" && f.is_visible_in_purchase !== false)
    .sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0));

  // Safeguard: Always ensure serial_no is present
  if (!filtered.some(f => f.field_name === "serial_no")) {
    filtered.unshift({
      field_name: "serial_no",
      label: "Serial / IMEI / Chassis",
      is_required: true,
      sort_order: 0
    });
  }
  return filtered;
}

function createDefaultSerialChild(parentProduct, parentRate = 0) {
  const defaultCost = Number(parentRate || parentProduct?.rate || parentProduct?.cost || parentProduct?.last_pur_price || 0);
  return {
    id: "s_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7),
    serial_no: "",
    serial_no2: "",
    color: "",
    processor: "",
    ram: "",
    storage: "",
    condition: "NEW",
    model_year: "",
    warranty_end: "",
    cost: defaultCost,
  };
}

function copySerialChild(parentId, childId, targetFieldName = null) {
  const item = cachedCartMap.get(String(parentId));
  if (!item || !Array.isArray(item.serial_items)) return;
  const idx = item.serial_items.findIndex(c => String(c.id) === String(childId));
  if (idx === -1) return;
  const src = item.serial_items[idx];
  const newChild = {
    ...src,
    id: "s_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7),
    serial_no: "", // Blank for new piece's IMEI/serial
    serial_no2: "",
  };
  item.serial_items.splice(idx + 1, 0, newChild);
  item.qty = item.serial_items.length;
  item.amount = item.serial_items.reduce((sum, s) => sum + (Number(s.cost) || 0), 0);
  saveCart(getCart());
  renderCart();
  setTimeout(() => {
    const row = cartBody?.querySelector(`.serial-child-row[data-child-id="${newChild.id}"]`);
    if (row) {
      const fieldToFocus = targetFieldName || main_serial_field;
      const inp = row.querySelector(`.serial-child-input[data-field-name="${fieldToFocus}"]`) || row.querySelector(".serial-child-input");
      if (inp) {
        inp.focus();
        if (inp.select) inp.select();
      }
    }
  }, 35);
}

function addSerialChild(parentId, afterChildId = null) {
  const item = cachedCartMap.get(String(parentId));
  if (!item) return;
  if (!Array.isArray(item.serial_items)) item.serial_items = [];
  const newChild = createDefaultSerialChild(item, item.rate || 0);
  if (afterChildId) {
    const idx = item.serial_items.findIndex(c => String(c.id) === String(afterChildId));
    if (idx !== -1) {
      item.serial_items.splice(idx + 1, 0, newChild);
    } else {
      item.serial_items.push(newChild);
    }
  } else {
    item.serial_items.push(newChild);
  }
  item.qty = item.serial_items.length;
  item.amount = item.serial_items.reduce((sum, s) => sum + (Number(s.cost) || 0), 0);
  saveCart(getCart());
  renderCart();
  setTimeout(() => {
    const row = cartBody?.querySelector(`.serial-child-row[data-child-id="${newChild.id}"]`);
    if (row) {
      const inp = row.querySelector(".serial-child-input");
      if (inp) {
        inp.focus();
        if (inp.select) inp.select();
      }
    }
  }, 35);
}

function removeSerialChild(parentId, childId) {
  const item = cachedCartMap.get(String(parentId));
  if (!item || !Array.isArray(item.serial_items)) return;
  const idx = item.serial_items.findIndex(c => String(c.id) === String(childId));
  item.serial_items = item.serial_items.filter(c => String(c.id) !== String(childId));
  if (item.serial_items.length === 0) {
    deleteCartItem(parentId);
    return;
  }
  item.qty = item.serial_items.length;
  item.amount = item.serial_items.reduce((sum, s) => sum + (Number(s.cost) || 0), 0);
  saveCart(getCart());
  renderCart();
  setTimeout(() => {
    const remainingRows = Array.from(cartBody?.querySelectorAll(`.serial-nested-row[data-parent-row-id="${parentId}"] .serial-child-row`) || []);
    if (remainingRows.length > 0) {
      const targetRow = remainingRows[Math.min(idx, remainingRows.length - 1)];
      const inp = targetRow?.querySelector(".serial-child-input");
      if (inp) {
        inp.focus();
        if (inp.select) inp.select();
      }
    }
  }, 35);
}

function renderSerialNestedTable(item, totalColumns, groupIdx = 0) {
  ensureSerialStyles();
  const fields = getSerialFieldsConfigForCategory(item.prod_categ);

  let headerHtml = `<th style="padding: 6px 8px; width: 32px; text-align: center; border-bottom: 2px solid #cbd5e1;">#</th>`;
  fields.forEach(f => {
    headerHtml += `<th style="padding: 6px 8px; text-align: left; border-bottom: 2px solid #cbd5e1;">${f.label}${f.is_required ? ' *' : ''}</th>`;
  });
  headerHtml += `<th style="padding: 6px 8px; width: 105px; text-align: right; border-bottom: 2px solid #cbd5e1;">Cost *</th>`;
  headerHtml += `<th style="padding: 6px 8px; width: 95px; text-align: center; border-bottom: 2px solid #cbd5e1;">Actions</th>`;

  let rowsHtml = "";
  (item.serial_items || []).forEach((child, idx) => {
    let cellsHtml = `
      <td style="padding: 4px 6px; text-align: center; color: #64748b; font-weight: 600;">
        ${idx + 1}
        <input type="hidden" class="serial-child-qty" value="1" />
      </td>`;

    fields.forEach(f => {
      const val = child[f.field_name] !== undefined && child[f.field_name] !== null ? child[f.field_name] : "";
      if (f.field_name === "condition") {
        cellsHtml += `
          <td style="padding: 4px 6px;">
            <select class="serial-child-input cart-input" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" data-field-name="condition" tabindex="0">
              <option value="NEW" ${val === "NEW" ? "selected" : ""}>New - Box Pack</option>
              <option value="USED" ${val === "USED" ? "selected" : ""}>Used - Direct Purchase</option>
              <option value="REFURB" ${val === "REFURB" ? "selected" : ""}>Refurbished</option>
              <option value="FAULTY" ${val === "FAULTY" ? "selected" : ""}>Faulty / Damaged</option>
            </select>
          </td>`;
      } else if (f.field_name === "warranty_end") {
        cellsHtml += `
          <td style="padding: 4px 6px;">
            <input type="date" value="${val}" class="serial-child-input cart-input" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" data-field-name="warranty_end" tabindex="0" />
          </td>`;
      } else {
        cellsHtml += `
          <td style="padding: 4px 6px;">
            <input type="text" value="${val}" placeholder="${f.label}" class="serial-child-input cart-input" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" data-field-name="${f.field_name}" ${f.is_required ? "required" : ""} tabindex="0" />
          </td>`;
      }
    });

    // Cost input
    cellsHtml += `
      <td style="padding: 4px 6px;">
        <input type="number" step="any" min="0" value="${child.cost !== undefined ? child.cost : 0}" class="serial-child-input serial-cost-input cart-input" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" data-field-name="cost" style="text-align: right; font-weight: 600;" required tabindex="0" />
      </td>`;

    // Action buttons: Copy same, Add row, Delete row
    cellsHtml += `
      <td style="padding: 4px 6px; text-align: center; white-space: nowrap;">
        <div class="serial-row-actions">
          <button type="button" class="btn-serial-action copy-serial-btn" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" title="Copy same (Duplicate specs)" tabindex="0">
            <i class="fa-solid fa-copy"></i>
          </button>
          <button type="button" class="btn-serial-action add-serial-child-btn" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" title="Add new empty row below" tabindex="0">
            <i class="fa-solid fa-plus"></i>
          </button>
          <button type="button" class="btn-serial-action remove-serial-btn" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}" title="Delete this serial piece" tabindex="0">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </td>`;

    rowsHtml += `<tr class="serial-child-row" data-parent-id="${item.cart_row_id}" data-child-id="${child.id}">${cellsHtml}</tr>`;
  });

  return `
    <tr class="serial-nested-row ${`serial-group-${groupIdx % 4}`}" data-parent-row-id="${item.cart_row_id}" style="border-top: none;">
      <td colspan="${totalColumns}" style="padding: 0; border-top: none; background: transparent;">
        <div class="serial-child-container" style="width: 92%; margin: 0 auto; margin-left: 4%; margin-bottom: 6px; background: #F8FAFC; border: 1px solid #E2E8F0; border-top: 0; border-radius: 0 0 8px 8px; padding: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; padding: 2px 4px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; background: #DBEAFE; color: #2563EB; border-radius: 4px; font-size: 10px;">
                <i class="fa-solid fa-turn-down" style="transform: rotate(270deg);"></i>
              </span>
              <strong style="color: #334155; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Item Serials / IMEIs</strong>
              <span style="background: #E2E8F0; color: #475569; font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 10px;">${item.serial_items?.length || 0} pieces</span>
            </div>
            <button type="button" class="btn small add-serial-btn" data-parent-row-id="${item.cart_row_id}" style="padding: 3px 10px; font-size: 11px; font-weight: 600; background: #2563EB; color: #ffffff; border: 1px solid #1D4ED8; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 4px;" title="Add another serial piece" tabindex="0">
              <i class="fa-solid fa-plus"></i>
              <span>Add Serial</span>
            </button>
          </div>
          <div style="overflow-x: auto; border: 1px solid #CBD5E1; border-radius: 6px; background: #ffffff;">
            <table class="serial-sub-table">
              <thead>
                <tr>
                  ${headerHtml}
                </tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
            </table>
          </div>
        </div>
      </td>
    </tr>
  `;
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
    const isSerial = String(product.tracking_type || "").toUpperCase() === "SERIAL";

    if (!multiline.checked) {
      const existingItem = productMap.get(String(productId));
      if (existingItem) {
        if (existingItem.is_serial || existingItem.tracking_type === "SERIAL") {
          if (!Array.isArray(existingItem.serial_items)) existingItem.serial_items = [];
          existingItem.serial_items.push(createDefaultSerialChild(product, existingItem.rate || 0));
          existingItem.qty = existingItem.serial_items.length;
          existingItem.amount = existingItem.serial_items.reduce((sum, s) => sum + (Number(s.cost) || 0), 0);
          continue;
        } else {
          existingItem.qty += qtyToAdd;
          applyCalculation(existingItem);
          continue;
        }
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
        dynamicFields[fieldName] = product[fieldName] !== undefined ? product[fieldName] : getDefaultDynamicFieldValue(fieldConfig);
      }
    }

    if (isSerial) {
      const defaultChild = createDefaultSerialChild(product, initialRate);
      const item = {
        cart_row_id: create_unique_row_no(),
        id: productId,
        product_description: product[POS_MAPPING.product.prod_name] || product.prod_name || product.product_description,
        prod_name_ur: product.prod_name_ur || "",
        tracking_type: "SERIAL",
        is_serial: true,
        serial_items: [defaultChild],
        qty: 1,
        packing_mode: Number(defaultModeId),
        prices,
        discounts,
        qtyFactors,
        uoms,
        rate: initialRate,
        discount_percent_per_item: 0,
        discount: 0,
        amount: Number(defaultChild.cost) || 0,
        prod_categ: product.category || product.category_id || product.prod_categ || "",
        ...dynamicFields
      };
      cart.push(item);
      if (!multiline.checked) {
        productMap.set(String(productId), item);
      }
      continue;
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


function getDefaultDynamicFieldValue(fieldConfig) {
  if (fieldConfig?.type === "date") {
    const date = new Date();
    date.setMonth(date.getMonth() + 1);

    // YYYY-MM-DD for <input type="date">
    return date.toISOString().split("T")[0];
  }

  return fieldConfig?.default ?? "";
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

    const discountAmt = (!applyRistrictionsInPurchase || window.companyConfigurations?.pos_discount_per_item)
      ? Number(item.discount || item.row_discount_amount || 0)
      : 0;
    const discountPct = item.row_discount_percent || 0;

    // Load custom dynamic row fields from the bill item
    const dynamicFields = {};
    if (window.PURCHASE_CART_ROW_FIELDS) {
      for (const [fieldName, fieldConfig] of Object.entries(window.PURCHASE_CART_ROW_FIELDS)) {
        dynamicFields[fieldName] = item[fieldName] !== undefined ? item[fieldName] : getDefaultDynamicFieldValue(fieldConfig);
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
      row_old_total_base_qty: item.row_old_total_base_qty !== undefined
        ? Number(item.row_old_total_base_qty)
        : (Number(item.qty || 0) + Number(item.foc_qty || 0)) * Number(item.pack_qty || 1),
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
  
  // cart.forEach((item) => {
    let serialGroupCounter = 0;
    cart.forEach((item) => {
      const isSerial = item.tracking_type === "SERIAL" || item.is_serial;
      //const isSerial = item.tracking_type === "SERIAL" || item.is_serial;
      const groupClass = isSerial ? `serial-group-${serialGroupCounter % 4}` : '';
      const groupIdx = serialGroupCounter;
      if(isSerial) serialGroupCounter++;
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

    // const isSerial = item.tracking_type === "SERIAL" || item.is_serial;
    const totalColumns = 8 + (window.PURCHASE_CART_ROW_FIELDS ? Object.keys(window.PURCHASE_CART_ROW_FIELDS).length : 0);

    if (isSerial) {
      const serialNestedTableHtml = renderSerialNestedTable(item, totalColumns, groupIdx);

      const row = `
      <tr class="cart-item-row serial-parent-row ${groupClass}" data-group="${groupIdx}" data-row-id="${item.cart_row_id}" style="background: #EFF6FF; border-bottom: none;">
        <td class="desc-cell" style="width: 200px;">
          <input type="text" value="${item.product_description} (${item.id})" readonly class="input-flat" style="width: 100%; font-weight: 600; color: #1E3A8A; background: transparent;" />
          <input type="hidden" value="${item.id}" name="item_id" />
        </td>
        <td style="width: 80px;">
          <input type="number" value="${item.qty}" readonly class="cart-input qty-input" style="width: 100%; background: #DBEAFE; font-weight: 600; text-align: center; cursor: not-allowed; border-color: #BFDBFE; color: #1E3A8A;" title="Calculated from child count" />
        </td>
        <td style="width: 80px;">
          <input type="text" value="Retail" readonly disabled class="cart-input input-flat" style="width: 100%; text-align: center; background: #DBEAFE; color: #64748B; border-color: #BFDBFE;" />
        </td>
        <td style="width: 100px;">
          <input type="text" value="-" disabled class="cart-input rate-input" style="width: 100%; text-align: center; background: #DBEAFE; color: #94A3B8; cursor: not-allowed; border-color: #BFDBFE;" title="Price is set individually per serial piece below" />
        </td>
        <td>
          <input type="number" value="0" disabled class="cart-input discount_percent_per_item-input" style="width: 100%; background: #DBEAFE; color: #94A3B8; text-align: center; border-color: #BFDBFE;" />
        </td>
        <td>
          <input type="number" value="0" disabled class="cart-input discount_per_item-input" style="width: 100%; background: #DBEAFE; color: #94A3B8; text-align: center; border-color: #BFDBFE;" />
        </td>
        <td style="width: 100px;">
          <input type="number" value="${amount.toFixed(2)}" readonly step="0.01" class="cart-input amount-input" style="width: 100%; font-weight: 700; color: #1E3A8A; text-align: right; background: #DBEAFE; border-color: #BFDBFE;" />
        </td>

        ${dynamicCells}
        <td style="width: 20px;">
          <button type="button" class="btn small remove-item-btn" data-row-id="${item.cart_row_id}" title="Delete item and all serials">×</button>
        </td>
      </tr>
      ${serialNestedTableHtml}`;
      htmlAccumulator += row;
    } else {
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
    }
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


// ______________________ Serial Table Keyboard Navigation ______________________
function handleSerialKeyNavigation(e, currentSerialRow) {
  const activeEl = document.activeElement;
  const tbody = currentSerialRow.closest("tbody");
  if (!tbody) return;

  const allRows = Array.from(tbody.querySelectorAll(".serial-child-row"));
  const rowIndex = allRows.indexOf(currentSerialRow);
  if (rowIndex === -1) return;

  const getRowControls = (r) =>
    Array.from(r.querySelectorAll(".serial-child-input, .btn-serial-action"))
      .filter((el) => !el.disabled && el.offsetParent !== null);

  const controls = getRowControls(currentSerialRow);
  const currentCtrlIndex = controls.indexOf(activeEl);

  const focusControl = (el) => {
    if (!el) return;
    tbody.querySelectorAll(".serial-child-row").forEach(r => r.classList.remove("active-serial-row"));
    const row = el.closest(".serial-child-row");
    if (row) row.classList.add("active-serial-row");
    el.focus();
    if (el.tagName === "INPUT" && el.type !== "hidden" && el.type !== "checkbox") {
      el.select?.();
    }
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  // 1. LEFT / RIGHT ARROWS
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    if (currentCtrlIndex === -1) return;

    let canMove = false;
    const isButton = activeEl.tagName === "BUTTON";
    const isSelect = activeEl.tagName === "SELECT";

    if (isButton || isSelect) {
      canMove = true;
    } else {
      const val = activeEl.value ?? "";
      const start = activeEl.selectionStart;
      const end = activeEl.selectionEnd;
      const hasSelection = typeof start === "number" && typeof end === "number" && start !== end;

      if (!hasSelection) {
        if (e.key === "ArrowLeft") {
          canMove = start === 0 || typeof start !== "number";
        } else if (e.key === "ArrowRight") {
          canMove = end === val.length || typeof end !== "number";
        }
      }
    }

    if (canMove) {
      if (e.key === "ArrowRight") {
        if (currentCtrlIndex + 1 < controls.length) {
          e.preventDefault();
          e.stopPropagation();
          focusControl(controls[currentCtrlIndex + 1]);
        } else if (rowIndex + 1 < allRows.length) {
          e.preventDefault();
          e.stopPropagation();
          const nextRowControls = getRowControls(allRows[rowIndex + 1]);
          if (nextRowControls.length) focusControl(nextRowControls[0]);
        }
      } else if (e.key === "ArrowLeft") {
        if (currentCtrlIndex - 1 >= 0) {
          e.preventDefault();
          e.stopPropagation();
          focusControl(controls[currentCtrlIndex - 1]);
        } else if (rowIndex - 1 >= 0) {
          e.preventDefault();
          e.stopPropagation();
          const prevRowControls = getRowControls(allRows[rowIndex - 1]);
          if (prevRowControls.length) focusControl(prevRowControls[prevRowControls.length - 1]);
        }
      }
    }
  }

  // 2. UP / DOWN ARROWS
  if (e.key === "ArrowUp" || e.key === "ArrowDown") {
    e.preventDefault();
    e.stopPropagation();

    if (e.key === "ArrowDown") {
      if (rowIndex + 1 < allRows.length) {
        const nextRow = allRows[rowIndex + 1];
        const nextControls = getRowControls(nextRow);
        const target = nextControls[currentCtrlIndex] || nextControls[nextControls.length - 1] || nextControls[0];
        focusControl(target);
      } else {
        // Step into next main cart row
        const nestedRow = currentSerialRow.closest(".serial-nested-row");
        let nextCartRow = nestedRow ? nestedRow.nextElementSibling : null;
        while (nextCartRow && !nextCartRow.classList.contains("cart-item-row")) {
          nextCartRow = nextCartRow.nextElementSibling;
        }
        if (nextCartRow) {
          const cartInput = nextCartRow.querySelector("input:not([type='hidden']):not([readonly]):not(:disabled), select:not(:disabled)");
          if (cartInput) {
            cartInput.focus();
            cartInput.select?.();
          }
        }
      }
    } else if (e.key === "ArrowUp") {
      if (rowIndex - 1 >= 0) {
        const prevRow = allRows[rowIndex - 1];
        const prevControls = getRowControls(prevRow);
        const target = prevControls[currentCtrlIndex] || prevControls[prevControls.length - 1] || prevControls[0];
        focusControl(target);
      } else {
        // Step into parent cart row or previous item
        const nestedRow = currentSerialRow.closest(".serial-nested-row");
        const parentId = nestedRow?.dataset.parentRowId;
        const parentRow = cartBody.querySelector(`tr.cart-item-row[data-row-id="${parentId}"]`);
        if (parentRow) {
          const prevCartRow = parentRow.previousElementSibling;
          if (prevCartRow && prevCartRow.classList.contains("cart-item-row")) {
            const prevInput = prevCartRow.querySelector("input:not([type='hidden']):not([readonly]):not(:disabled), select:not(:disabled)");
            if (prevInput) {
              prevInput.focus();
              prevInput.select?.();
            }
          } else {
            const removeBtn = parentRow.querySelector(".remove-item-btn");
            if (removeBtn) removeBtn.focus();
          }
        }
      }
    }
  }

  // 3. ENTER KEY
  if (e.key === "Enter") {
    if (activeEl.tagName === "BUTTON") {
      return; // standard button click handles it
    }

    const fieldName = activeEl.dataset?.fieldName;
    const parentId = currentSerialRow.dataset?.parentId;
    const childId = currentSerialRow.dataset?.childId;

    // Fast Barcode Tracking: If on main_serial_field, Enter creates duplicate row and keeps focus on the same field
    if (fieldName === main_serial_field) {
      e.preventDefault();
      e.stopPropagation();

      const item = cachedCartMap.get(String(parentId));
      if (item && Array.isArray(item.serial_items)) {
        const child = item.serial_items.find(c => String(c.id) === String(childId));
        if (child) {
          child[fieldName] = activeEl.value;
        }
      }

      copySerialChild(parentId, childId, main_serial_field);
      return;
    }

    const isCostInput = activeEl.classList.contains("serial-cost-input") || (activeEl.dataset?.fieldName === "cost");
    if (isCostInput) {
      e.preventDefault();
      e.stopPropagation();
      if (rowIndex + 1 < allRows.length) {
        const nextControls = getRowControls(allRows[rowIndex + 1]);
        if (nextControls.length) focusControl(nextControls[0]);
      } else {
        const parentId = currentSerialRow.dataset.parentId;
        addSerialChild(parentId);
      }
    } else if (currentCtrlIndex !== -1 && currentCtrlIndex + 1 < controls.length) {
      e.preventDefault();
      e.stopPropagation();
      focusControl(controls[currentCtrlIndex + 1]);
    }
  }
}

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

    // Active row highlight on focusin
    cartBody.addEventListener("focusin", (e) => {
      const serialRow = e.target.closest(".serial-child-row");
      if (serialRow) {
        const tbody = serialRow.closest("tbody");
        if (tbody) {
          tbody.querySelectorAll(".serial-child-row").forEach(r => r.classList.remove("active-serial-row"));
        }
        serialRow.classList.add("active-serial-row");
      }
    });

    // Keyboard navigation (Arrow keys + Enter)
    cartBody.addEventListener("keydown", (e) => {
      const serialRow = e.target.closest(".serial-child-row");
      if (serialRow) {
        handleSerialKeyNavigation(e, serialRow);
        return;
      }

      // If ArrowDown pressed on a serial parent row, step into the first serial row
      const parentRow = e.target.closest(".serial-parent-row");
      if (parentRow && (e.key === "ArrowDown" || e.key === "Enter")) {
        const parentId = parentRow.dataset.rowId;
        const nestedRow = cartBody.querySelector(`.serial-nested-row[data-parent-row-id="${parentId}"]`);
        if (nestedRow) {
          const firstInput = nestedRow.querySelector(".serial-child-input");
          if (firstInput) {
            e.preventDefault();
            firstInput.focus();
            if (firstInput.select) firstInput.select();
          }
        }
      }
    });

    // Live serial inputs update
    cartBody.addEventListener("input", (e) => {
      const serialInput = e.target.closest(".serial-child-input");
      if (serialInput) {
        const parentId = serialInput.dataset.parentId;
        const childId = serialInput.dataset.childId;
        const fieldName = serialInput.dataset.fieldName;
        const item = cachedCartMap.get(String(parentId));
        if (item && Array.isArray(item.serial_items)) {
          const child = item.serial_items.find(c => String(c.id) === String(childId));
          if (child) {
            if (fieldName === "cost") {
              child.cost = Number(serialInput.value) || 0;
              item.amount = item.serial_items.reduce((sum, s) => sum + (Number(s.cost) || 0), 0);
              const parentRow = cartBody.querySelector(`tr.cart-item-row[data-row-id="${parentId}"]`);
              if (parentRow) {
                const amtInput = parentRow.querySelector(".amount-input");
                if (amtInput) amtInput.value = item.amount.toFixed(2);
              }
              let cartTotal = 0;
              getCart().forEach(it => { cartTotal += (it.amount || 0); });
              if (itemTotal) itemTotal.textContent = cartTotal.toFixed(2);
              if (netTotal) netTotal.textContent = cartTotal.toFixed(2);
            } else {
              child[fieldName] = serialInput.value;
            }
            saveCart(getCart());
          }
        }
      }
    });

    cartBody.addEventListener("change", (e) => {
      const serialInput = e.target.closest(".serial-child-input");
      if (serialInput && serialInput.tagName === "SELECT") {
        const parentId = serialInput.dataset.parentId;
        const childId = serialInput.dataset.childId;
        const fieldName = serialInput.dataset.fieldName;
        const item = cachedCartMap.get(String(parentId));
        if (item && Array.isArray(item.serial_items)) {
          const child = item.serial_items.find(c => String(c.id) === String(childId));
          if (child) {
            child[fieldName] = serialInput.value;
            saveCart(getCart());
          }
        }
      }
    });

    cartBody.addEventListener("click", (e) => {
      // 1. Copy same serial child row
      const copyBtn = e.target.closest(".copy-serial-btn");
      if (copyBtn) {
        const parentId = copyBtn.dataset.parentId;
        const childId = copyBtn.dataset.childId;
        copySerialChild(parentId, childId);
        return;
      }

      // 2. Add new serial row below current
      const addRowBtn = e.target.closest(".add-serial-child-btn");
      if (addRowBtn) {
        const parentId = addRowBtn.dataset.parentId;
        const childId = addRowBtn.dataset.childId;
        addSerialChild(parentId, childId);
        return;
      }

      // 3. Add serial child row from header button
      const addSerialBtn = e.target.closest(".add-serial-btn");
      if (addSerialBtn) {
        const parentRowId = addSerialBtn.dataset.parentRowId;
        addSerialChild(parentRowId);
        return;
      }

      // 4. Remove serial child row
      const removeSerialBtn = e.target.closest(".remove-serial-btn");
      if (removeSerialBtn) {
        const parentId = removeSerialBtn.dataset.parentId;
        const childId = removeSerialBtn.dataset.childId;
        removeSerialChild(parentId, childId);
        return;
      }

      // 5. Remove main cart row
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

  // Serial parent rows are calculated strictly from child serial items
  if (item.is_serial || item.tracking_type === "SERIAL") {
    return;
  }

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

  if (!applyRistrictionsInPurchase || window.companyConfigurations?.pos_discount_per_item) {
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
    if (!applyRistrictionsInPurchase || window.companyConfigurations?.pos_discount_per_item) {
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
