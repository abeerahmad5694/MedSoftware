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

export const supplierInvNo = document.getElementById("supl-inv");
export const supplierInvDate = document.getElementById("supl-date");
export const ourRef = document.getElementById("our-ref");
export const ourRefDate = document.getElementById("our-ref-date");
export const deliveredBy = document.getElementById("delivered-by");
export const freightAmount = document.getElementById("freight-amt");
export const labourAmount = document.getElementById("labour-amt");
export const unloadAmount = document.getElementById("unload-amt");
export const date = document.getElementById('date')
export const unloadAccCode = document.getElementById('unload_acc_code')
export const labourAccCode = document.getElementById('labour_acc_code')
export const freightAccCode = document.getElementById('freight_acc_code')


export const purchaseReturnRadio = document.getElementById('return')
export const purchaseRadio = document.getElementById('purchase')
export const btnDeleteBill = document.getElementById('btnDeleteBill')

export const searchAccountBtn = document.getElementById('search-account-btn')


// For groups, export the NodeList directly
export const priceModeRadios = document.querySelectorAll('input[name="price_mode"]');

// Helper if you need to query later: not needed now but useful
export const getSelectedRow = () => document.querySelector(".cart-item-row.selected-row");
export const getAllCartRows = () => document.querySelectorAll(".cart-item-row");
export const getCartRowById = (id) => document.querySelector(`.cart-item-row[data-row-id="${id}"]`);

export let billTypeRadioButton = document.querySelector('input[name="bill_type"]:checked');





















