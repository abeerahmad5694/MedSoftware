export const hidden_bill_no = document.getElementById('old_bill_no');
export const paymentMode = document.getElementById("payment-mode");
export const cardDetails = document.getElementById("card-details");
export const cardNumber = document.getElementById("card-number");
export const barcodeScanCheckbox = document.getElementById("barcode-scan");
export const old_inv_search = document.getElementById("invoice-number");

export const discountInput = document.getElementById("discount-percent");
export const load_bill = document.getElementById("Load-bill");
export const searchInput = document.querySelector("#product-search");
export const btnSaveBill = document.querySelector("#btn-save-bill");
export const btnNewBill = document.querySelector("#btn-new-bill");
export const multiline = document.querySelector("#multi-line");

export const deliveryCharges = document.getElementById("delivery-charges");
export const taxPercentInput = document.getElementById("tax-percent");
export const taxAmountInput = document.getElementById("tax-amount");
export const mscChargesInput = document.getElementById("msc-charges");
export const receivedAmount = document.getElementById("received-amount");
export const remarksInput = document.querySelector("#remarks-input");
export const changeAmount = document.querySelector("#change-amount");
export const salesMan = document.getElementById('sales-man');
export const accCode = document.getElementById('acc_code');
export const lastBillAmount = document.getElementById("last-bill-amount");
export const loader = document.getElementById("loader");
export const enterCodeLabel = document.getElementById("enter-code-label");

export const btnConvertToWholesale = document.getElementById('btn-convert-to-wholesale');
export const btnCashPay = document.getElementById("btn-cash-pay");
export const btnCashReceive = document.getElementById("btn-cash-receive");

// Newly added DOM elements to prevent in-function querySelector/getElementById calls
export const cartBody = document.getElementById("cart-body");
export const itemTotal = document.getElementById("item-total");
export const netTotal = document.getElementById("net-total");
export const bankAmountInput = document.getElementById("bank-amount-input");
export const discountAmount = document.getElementById("discount-amount");
export const deliveryChargesDisplay = document.getElementById("delivery-charges-display");
export const confirmPrint = document.getElementById("confirmPrint");
export const directPrinting = document.getElementById("direct-printing");
export const cashAmount = document.getElementById("cash-amount");
export const bankAmount = document.getElementById("bank-amount");
export const receivedAmountLabel = document.getElementById("received-amount-label");
export const changeAmountLabel = document.getElementById("change-amount-label");
export const zoomInBtn = document.getElementById("zoomInBtn");
export const zoomOutBtn = document.getElementById("zoomOutBtn");
export const btnSearch = document.getElementById("btn-search");
export const btnConvertToBill = document.getElementById("btn-convert-to-bill");
export const btnSelectClient = document.getElementById("btn-select-client");

export const btnDeleteBill = document.getElementById('btnDeleteBill')
// export const date = document.getElementById("date");

// For groups, export the NodeList directly
export const priceModeRadios = document.querySelectorAll('input[name="price_mode"]');

// Helper if you need to query later: not needed now but useful
export const getSelectedRow = () => document.querySelector(".cart-item-row.selected-row");
export const getAllCartRows = () => document.querySelectorAll(".cart-item-row");
export const getCartRowById = (id) => document.querySelector(`.cart-item-row[data-row-id="${id}"]`);
