import {
  getCookie,
  showToast,
} from "./helper_func.js";
import { barcode_config } from './waste/pos_features.js';
import {
  getDB,
  addRecord,
  deleteRecord,
  getAllRecords
} from "/static/myglobal/js/services/local_storage/session_storage_manager.js";

const STORE_NAME = "pendingPurchaseBills";

function scan_barcode(query) {
  try {
    const price_base = barcode_config.price_base;
    const total_bc_digits = barcode_config.total_bc_digits;
    const left_delete = barcode_config.left_delete;
    const right_delete = barcode_config.right_delete;
    const trimmed = query.slice(left_delete, total_bc_digits - right_delete);

    const item_code = trimmed.slice(0, barcode_config.item_bc);
    const weight = trimmed.slice(barcode_config.item_bc);
    const kg = weight.slice(0, barcode_config.kg);
    const grm = weight.slice(barcode_config.kg);
    const weight_total = `${kg}.${grm}`;
    return { query, item_code, weight_total };
  } catch (er) {
    alert('some thing wrong in barcode');
  }
}

// Keep backward compatible openDB that returns the DB connection
async function openDB() {
  return await getDB();
}

async function saveBillOffline(payload) {
  try {
    const result = await addRecord(STORE_NAME, payload);
    console.log(" Bill added to pendingPurchaseBills:", result);
    return result;
  } catch (err) {
    console.error(" Failed to add bill:", err);
    throw err;
  }
}

async function syncoffline_bills() {
  let totalSynced = 0;
  let totalFailed = 0;
  const failedBillDetails = [];

  showToast("🌐 Online: Syncing offline bills...", "info");

  let records;
  try {
    await openDB();
    records = await getAllRecords(STORE_NAME);
  } catch (dbErr) {
    console.error("[Purchase Sync] Failed to read local DB:", dbErr);
    showToast("❌ Could not read offline bills from local storage.", "error");
    alert(`Sync Error: Could not read offline bills.\nDetails: ${dbErr.message || dbErr}`);
    return;
  }

  if (!records || records.length === 0) {
    showToast("ℹ️ No offline bills to sync.", "info");
    return;
  }

  showToast(`📝 Found ${records.length} offline bill(s). Syncing...`, "info");

  const chunkSize = 100;
  const allBatches = [];
  for (let i = 0; i < records.length; i += chunkSize) {
    allBatches.push(records.slice(i, i + chunkSize));
  }

  const concurrency = 3;
  for (let i = 0; i < allBatches.length; i += concurrency) {
    const batchGroup = allBatches.slice(i, i + concurrency);
    await Promise.all(
      batchGroup.map(async (chunk) => {
        let data = null;
        try {
          const res = await fetch(window.app_constants.save_purchase_bills_api || '/purchase/api/save_bills/', {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(chunk),
          });

          // Check HTTP-level errors first
          if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Server returned HTTP ${res.status}: ${errText.slice(0, 200)}`);
          }

          data = await res.json();
        } catch (networkErr) {
          // Network failure or HTTP error — do NOT delete local records
          console.error("[Purchase Sync] Network/HTTP error for batch:", networkErr);
          totalFailed += chunk.length;
          chunk.forEach(b => failedBillDetails.push({
            local_id: b.local_id,
            reason: `Network error: ${networkErr.message || networkErr}`
          }));
          showToast(`❌ Network error syncing ${chunk.length} bill(s). Will retry later.`, "error");
          return; // leave local records intact
        }

        // Server responded — check application-level success
        if (data && data.success) {
          // 100% confirmed: now safe to delete local copies
          try {
            await Promise.all(chunk.map(b => deleteRecord(STORE_NAME, b.local_id)));
            totalSynced += chunk.length;
            showToast(`✅ Synced ${chunk.length} bill(s) successfully.`, "success");
          } catch (deleteErr) {
            // Records were saved but local delete failed
            console.error("[Purchase Sync] Failed to delete local records after successful sync:", deleteErr);
            showToast("⚠️ Bills saved to server but could not remove local copies.", "warning");
          }
        } else {
          // Server explicitly returned failure — keep local records safe
          const serverMsg = (data && data.message) ? data.message : "Unknown server error.";
          console.error("[Purchase Sync] Server rejected batch:", serverMsg, "| Saved:", data?.saved_count, "| Failed:", data?.failed_count);
          totalFailed += chunk.length;
          chunk.forEach(b => failedBillDetails.push({
            local_id: b.local_id,
            reason: serverMsg
          }));
          showToast(`❌ Server error for batch: ${serverMsg}`, "error");
        }
      })
    );
  }

  // Final summary
  if (totalFailed === 0 && totalSynced > 0) {
    showToast(`🎉 All ${totalSynced} bill(s) synced successfully!`, "success");
  } else if (totalFailed > 0) {
    const summary = `⚠️ Sync complete: ${totalSynced} synced, ${totalFailed} failed.\n\nFailed bill IDs:\n` +
      failedBillDetails.map(f => `• Local ID ${f.local_id}: ${f.reason}`).join("\n");
    console.warn("[Purchase Sync] Failures:", failedBillDetails);
    showToast(`⚠️ ${totalSynced} synced, ${totalFailed} failed. Check console for details.`, "error");
    alert(summary);
  } else if (totalSynced === 0 && totalFailed === 0) {
    showToast("ℹ️ Nothing to sync.", "info");
  }
}

let cachedInventory = null;
let cachedInventoryTime = 0;

function clearInventoryCache() {
  cachedInventory = null;
  cachedInventoryTime = 0;
}

async function searchProductOffline(term) {
  if (!window.IndexDBConfig) {
    console.error("IndexDBConfig is not available on window.");
    return [];
  }

  try {
    const now = Date.now();
    // Cache invalidation: refetch if null or older than 60 seconds
    if (!cachedInventory || (now - cachedInventoryTime > 60000)) {
      cachedInventory = await window.IndexDBConfig.get_all('inventory');
      cachedInventoryTime = now;
    }
    const products = cachedInventory;
    let searchTerm = term.trim();

    if (searchTerm.length === barcode_config.total_bc_digits) {
      const parsed = scan_barcode(searchTerm);
      if (parsed?.item_code) {
        searchTerm = parsed.item_code;
      }
    }

    const result = products.filter((p) => {
      return (
        (p.manualbc && p.manualbc.toLowerCase() === searchTerm.toLowerCase()) ||
        String(p.inv_id || "") === searchTerm ||
        String(p.id || "") === searchTerm ||
        (p.prod_name && p.prod_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (p.item_name && p.item_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        String(p.barcode || "").trim() === searchTerm
      );
    });

    return result;
  } catch (err) {
    console.error("Error searching product offline:", err);
    return [];
  }
}

export {
  openDB,
  saveBillOffline,
  syncoffline_bills,
  searchProductOffline,
  scan_barcode,
  clearInventoryCache
};