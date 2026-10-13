// export * from "./bill_crud.js";




// async function fetchBill(voucherNo = null, load_old_bill = false) {
//   const url = voucherNo
//     ? window.app_constants.get_purchase_bill_api 
//       ? window.app_constants.get_purchase_bill_api + `${encodeURIComponent(voucherNo)}` 
//       : `/purchase/api/get_bill/${encodeURIComponent(voucherNo)}/`
//     : window.app_constants.get_purchase_bill_api;

//   try {
//     const res = await fetch(url);
//     if (!res.ok) {
//       return alert("Network error fetching bill.", "error");
//     }
//     const data = await res.json();

//     if (!data.success) {
//       return alert(data.message || "Bill not found", "error");
//     }
    
//     console.log('bill', data);
//     const bill = data.data;

//     if (load_old_bill) {
//       loadBillIntoCart(bill);

//       // Supplier card
//       const supplierCode = document.getElementById('supplier-code');
//       const supplierName = document.getElementById('supplier-name');
//       const supplierAddress = document.getElementById('supplier-address');
//       const supplierTele = document.getElementById('supplier-tele');
//       if (supplierCode) supplierCode.value = bill.header_acc_code || '';
//       if (supplierName) supplierName.value = bill.user || ''; // if you store supplier name separately, use that
//       // if (supplierAddress) supplierAddress.value = bill.header_address || '';
//       // if (supplierTele) supplierTele.value = bill.header_tele || '';

//       // Invoice details card
//       const suplInv = document.getElementById('supl-inv');
//       const suplDate = document.getElementById('supl-date');
//       const ourRef = document.getElementById('our-ref');
//       const ourRefDate = document.getElementById('our-ref-date');
//       const deliveredBy = document.getElementById('delivered-by');
//       const freightAmt = document.getElementById('freight-amt');
//       const labourAmt = document.getElementById('labour-amt');
//       const unloadAmt = document.getElementById('unload-amt');

//       if (suplInv) suplInv.value = bill.header_supl_inv_no || '';
//       if (suplDate) suplDate.value = bill.header_supl_inv_date ? formatDateForInput(bill.header_supl_inv_date) : '';
//       if (ourRef) ourRef.value = bill.header_our_ref || '';
//       if (ourRefDate) ourRefDate.value = bill.header_our_ref_date ? formatDateForInput(bill.header_our_ref_date) : '';
//       if (deliveredBy) deliveredBy.value = bill.header_delivery_person || '';
//       if (freightAmt) freightAmt.value = bill.header_freight_amount ?? '0.00';
//       if (labourAmt) labourAmt.value = bill.header_labour_amount ?? '0.00';
//       if (unloadAmt) unloadAmt.value = bill.header_unload_amount ?? '0.00';

//       // Invoice summary card
//       const invoiceNumber = document.getElementById('invoice-number');
//       const dateInput = document.getElementById('date');
//       if (invoiceNumber) invoiceNumber.value = bill.bill_no || '';
//       if (dateInput) dateInput.value = bill.date ? formatDateForInput(bill.date) : '';

//       // Hidden fields
//       const oldBillNo = document.getElementById('old_bill_no');
//       const accCode = document.getElementById('acc_code');
//       if (oldBillNo) oldBillNo.value = bill.bill_no || '';
//       if (accCode) accCode.value = bill.header_acc_code || '';

//       // Totals section
//       const discountInput = document.getElementById('discount-percent');
//       const deliveryCharges = document.getElementById('delivery-charges');
//       const deliveryChargesDisplay = document.getElementById('delivery-charges-display');
//       const itemTotal = document.getElementById('item-total');
//       const netTotal = document.getElementById('net-total');
      
//       if (discountInput) discountInput.value = bill.header_discount_percent ?? 0;
//       if (deliveryCharges) deliveryCharges.value = bill.header_delivery_charges ?? 0;
//       if (deliveryChargesDisplay) deliveryChargesDisplay.textContent = (bill.header_delivery_charges ?? 0).toFixed(2);
//       if (itemTotal) itemTotal.textContent = (bill.header_item_total ?? 0).toFixed(2);
//       if (netTotal) netTotal.textContent = (bill.header_net_total ?? 0).toFixed(2);

//       // Payment section
//       const receivedAmount = document.getElementById('received-amount');
//       const changeAmount = document.getElementById('change-amount');
//       const paymentMode = document.getElementById('payment-mode');
//       const cashAmount = document.getElementById('cash-amount-input');
//       const bankAmount = document.getElementById('bank-amount-input');
//       const cardNumber = document.getElementById('card-number');

//       if (paymentMode) {
//         // header_payment_mode: 1=cash, 2=card, 3=dual - adjust to your select values
//         if (bill.header_payment_mode == 1) paymentMode.value = 'cash';
//         else if (bill.header_payment_mode == 2) paymentMode.value = 'card';
//         else if (bill.header_payment_mode == 3) paymentMode.value = 'dual';
//       }
//       if (receivedAmount) receivedAmount.value = bill.header_total_paid ?? 0;
//       if (changeAmount) changeAmount.textContent = (bill.header_change_amount ?? 0).toFixed(2);
//       if (cashAmount) cashAmount.value = bill.header_cash_paid ?? 0;
//       if (bankAmount) bankAmount.value = bill.header_bank_paid ?? 0;
//       if (cardNumber) cardNumber.value = bill.header_card_last4 ? `**** **** **** ${bill.header_card_last4}` : "";

//       // Remarks + others
//       const remarksInput = document.getElementById('remarks-input');
//       const salesMan = document.getElementById('sales-man');
//       if (remarksInput) remarksInput.value = bill.header_remarks || "";
//       if (salesMan) salesMan.value = bill.salesman || "";

//       // Extra header fields you return but don't have inputs for - store in hidden or dataset if needed
//       const lastBillAmount = document.getElementById('last-bill-amount');
//       if (lastBillAmount && bill.header_acc_code && bill.header_acc_code != 112000001) {
//         lastBillAmount.style.display = 'block';
//         lastBillAmount.innerHTML = 'Account Code: ' + bill.header_acc_code;
//       }

//       // Set edit mode flags
//       Edit_mode = true;
//       Edit_voucher_no = bill.bill_no;
//       if (hidden_bill_no) hidden_bill_no.value = bill.bill_no;

//       // Trigger UI updates
//       if (typeof handlePaymentModeChange === 'function') handlePaymentModeChange();
//       renderCart(getCart());
//       refreshCartUI();
//       if (typeof updateTotals === 'function') updateTotals();

//     } else {
//       const receiptData = buildReceiptData({}, false, bill);
//       call_Receipt_func(receiptData);
//     }
//   } catch (err) {
//     console.error(err);
//     alert("Network error fetching bill.", "error");
//   }
// }

// // Helper: convert MM-DD-YYYY to YYYY-MM-DD for input[type=date]
// function formatDateForInput(dateStr) {
//   if (!dateStr) return '';
//   // Handles MM-DD-YYYY from strftime('%m-%d-%Y')
//   const parts = dateStr.split('-');
//   if (parts.length === 3) {
//     const [mm, dd, yyyy] = parts;
//     return `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
//   }
//   // If already YYYY-MM-DD or ISO, just take first 10 chars
//   return dateStr.substring(0, 10);
// }


// async function fetchBill(voucherNo = null, load_old_bill = false) {
//   const url = voucherNo
//     ? window.app_constants.get_purchase_bill_api ? window.app_constants.get_purchase_bill_api + `${encodeURIComponent(voucherNo)}` : `/purchase/api/get_bill/${encodeURIComponent(voucherNo)}/`
//     : window.app_constants.get_purchase_bill_api;
//   // console.log('caled fecthc', url);

//   try {
//     const res = await fetch(url);
//     if (!res.ok) {
//       return alert("Network error fetching bill.", "error");
//     }
//     const data = await res.json();

//     if (!data.success) {
//       return alert(data.message || "Bill not found", "error");
//     }
//     console.log('bill', data)
//     if (load_old_bill) {
//       console.log(data.data)
//       loadBillIntoCart(data.data);

//       const bill = data.data;
//       // if (bill.header_payment_mode == 1) {
//       //   paymentMode.value = 'cash';
//       //   receivedAmount.value = bill.header_total_paid || 0;
//       // } else if (bill.header_payment_mode == 2) {
//       //   paymentMode.value = 'card';
//       //   receivedAmount.value = bill.header_total_paid || 0;
//       // } else if (bill.header_payment_mode == 3) {
//       //   paymentMode.value = 'dual';
//       //   receivedAmount.value = bill.header_cash_paid || 0;
//       //   changeAmount.value = bill.header_card_paid || 0;
//       // }
//       // handlePaymentModeChange();
//       if (cardNumber) cardNumber.value = bill.header_card_last4 ? `*******${bill.header_card_last4}` : "";

//       if (bill.header_acc_code !== 112000001) lastBillAmount.innerHTML = 'Account Code: ' + bill.header_acc_code;

//       discountInput.value = bill.header_discount_percent || 0;
//       deliveryCharges.value = bill.header_delivery_charges || 0;
//       remarksInput.value = bill.header_remarks || "";
//       if (hidden_bill_no) hidden_bill_no.value = bill.bill_no;

//       Edit_mode = true;
//       Edit_voucher_no = bill.voucher_no || bill.bill_no;

//       renderCart(getCart());
//       refreshCartUI();
//     } else {
//       const receiptData = buildReceiptData({}, false, data.data);
//       call_Receipt_func(receiptData);
//     }
//   } catch (err) {
//     console.error(err);
//     alert("Network error fetching bill.", "error");
//   }
// }













// import {
//   getCookie,
//   showToast,
// } from "./helper_func.js";
// import { barcode_config } from './waste/pos_features.js';

// function scan_barcode(query) {
//   try {
//     const price_base = barcode_config.price_base;
//     const total_bc_digits = barcode_config.total_bc_digits;
//     const left_delete = barcode_config.left_delete;
//     const right_delete = barcode_config.right_delete;
//     const trimmed = query.slice(left_delete, total_bc_digits - right_delete);

//     const item_code = trimmed.slice(0, barcode_config.item_bc);
//     const weight = trimmed.slice(barcode_config.item_bc);
//     const kg = weight.slice(0, barcode_config.kg);
//     const grm = weight.slice(barcode_config.kg);
//     const weight_total = `${kg}.${grm}`;
//     return { query, item_code, weight_total };
//   } catch (er) {
//     alert('some thing wrong in barcode');
//   }
// }

// function openDB() {
//   return new Promise((resolve, reject) => {
//     const req = indexedDB.open("POS_DB", 2); // upgraded version
//     req.onupgradeneeded = (e) => {
//       const db = e.target.result;

//       // PENDING BILLS store (keep this store for offline POS transactions)
//       if (!db.objectStoreNames.contains("pendingBills")) {
//         const pending = db.createObjectStore("pendingBills", {
//           keyPath: "local_id",
//           autoIncrement: true,
//         });
//         pending.createIndex("synced", "synced", { unique: false });
//       }
//     };
//     req.onsuccess = (e) => resolve(e.target.result);
//     req.onerror = (e) => reject(e);
//   });
// }

// async function saveBillOffline(payload) {
//   const db = await openDB().catch((err) => {
//     console.error(" Failed to open DB", err);
//   });
//   if (!db) return;

//   const tx = db.transaction("pendingBills", "readwrite");
//   const store = tx.objectStore("pendingBills");

//   const req = store.add(payload);

//   req.onsuccess = () => console.log(" Bill added to pendingBills:", req.result);
//   req.onerror = (e) => console.error(" Failed to add bill:", e.target.error);

//   tx.onerror = (e) => console.error(" Transaction error:", e.target.error);
//   tx.onabort = (e) => console.error(" Transaction aborted:", e.target.error);

//   return new Promise((resolve, reject) => {
//     tx.oncomplete = () => resolve(req.result);
//     tx.onerror = () => reject(req.error);
//   });
// }



// async function syncoffline_bills() {
//   showToast("🌐 Online: Syncing started...", "info");
//   const db = await openDB();
//   const store = db
//     .transaction("pendingBills", "readonly")
//     .objectStore("pendingBills");

//   const chunkSize = 100; // batch size
//   let batch = [];
//   const allBatches = [];

//   // Use cursor to stream records without loading all into memory
//   await new Promise((resolve) => {
//     const cursorReq = store.openCursor();
//     cursorReq.onsuccess = (e) => {
//       const cursor = e.target.result;
//       if (cursor) {
//         batch.push(cursor.value);
//         if (batch.length === chunkSize) {
//           allBatches.push([...batch]);
//           batch = [];
//         }
//         cursor.continue();
//       } else {
//         if (batch.length) allBatches.push([...batch]); // remaining batch
//         resolve();
//       }
//     };
//     cursorReq.onerror = () => resolve();
//   });

//   showToast(`📝 Total batches to sync: ${allBatches.length}`, "info");

//   // Send batches concurrently (3 at a time for example)
//   const concurrency = 3;
//   for (let i = 0; i < allBatches.length; i += concurrency) {
//     const batchGroup = allBatches.slice(i, i + concurrency);
//     await Promise.all(
//       batchGroup.map(async (chunk) => {
//         // console.log('chunk=============',chunk)
//         try {
//           // console.log('sasfk',window.app_constants.save_sale_bills_api )
//           // const res = await fetch("/sale/sync_bills/", {
//           const res = await fetch(window.app_constants.save_sale_bills_api || '/sale/api/save_bills/', {
//             method: "POST",
//             headers: {
//               "Content-Type": "application/json",
//               "X-CSRFToken": getCookie("csrftoken"),
//             },
//             body: JSON.stringify(chunk),
//           });
//           const data = await res.json();
//           if (data.success) {
//             const delTx = db.transaction("pendingBills", "readwrite");
//             const delStore = delTx.objectStore("pendingBills");
//             await Promise.all(
//               chunk.map(
//                 (b) =>
//                   new Promise((res, rej) => {
//                     const req = delStore.delete(b.local_id);
//                     req.onsuccess = () => res();
//                     req.onerror = () => rej(req.error);
//                   })
//               )
//             );
//             await new Promise((r) => {
//               delTx.oncomplete = r;
//               delTx.onerror = r;
//             });
//             showToast(`✅ Synced batch of ${chunk.length} bills`, "success");
//           } else {
//             alert(data.message);
//           }
//         } catch (e) {
//           showToast("❌ Batch sync failed", "error");
//           return;
//         }
//       })
//     );
//   }

//   showToast("🎉 All pending bills synced successfully!", "success");
// }

// let cachedInventory = null;
// let cachedInventoryTime = 0;

// function clearInventoryCache() {
//   cachedInventory = null;
//   cachedInventoryTime = 0;
// }

// async function searchProductOffline(term) {
//   // Access the window-scoped IndexDBConfig from indexdb_config.js
//   if (!window.IndexDBConfig) {
//     console.error("IndexDBConfig is not available on window.");
//     return [];
//   }

//   try {
//     const now = Date.now();
//     // Cache invalidation: refetch if null or older than 60 seconds
//     if (!cachedInventory || (now - cachedInventoryTime > 60000)) {
//       cachedInventory = await window.IndexDBConfig.get_all('inventory');
//       cachedInventoryTime = now;
//     }
//     const products = cachedInventory;
//     let searchTerm = term.trim();

//     if (searchTerm.length === barcode_config.total_bc_digits) {
//       const parsed = scan_barcode(searchTerm);
//       if (parsed?.item_code) {
//         searchTerm = parsed.item_code;
//       }
//     }

//     const result = products.filter((p) => {
//       return (
//         (p.manualbc && p.manualbc.toLowerCase() === searchTerm.toLowerCase()) ||
//         String(p.inv_id || "") === searchTerm ||
//         String(p.id || "") === searchTerm ||
//         (p.product_description && p.product_description.toLowerCase().includes(searchTerm.toLowerCase())) ||
//         (p.item_name && p.item_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
//         String(p.barcode || "").trim() === searchTerm
//       );
//     });

//     return result;
//   } catch (err) {
//     console.error("Error searching product offline:", err);
//     return [];
//   }
// }

// export {
//   openDB,
//   saveBillOffline,
//   syncoffline_bills,
//   searchProductOffline,
//   scan_barcode,
//   clearInventoryCache
// };