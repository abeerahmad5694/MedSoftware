/**
 * Highly optimized, centralized IndexedDB Manager.
 * Caches database connections to eliminate connection overhead.
 */

const DB_NAME = "POS_DB";
const DB_VERSION = 3; // Bumped to 3 to add cart stores and quotation store

let cachedDB = null;
let dbPromise = null;

export function getDB() {
  if (cachedDB) return Promise.resolve(cachedDB);
  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = (e) => {
      const db = e.target.result;

      // Define all required object stores (tables)
      const stores = [
        { name: "pendingBills", keyPath: "local_id", autoIncrement: true, index: "synced" },
        { name: "pendingPurchaseBills", keyPath: "local_id", autoIncrement: true, index: "synced" },
        { name: "pendingQuotationBills", keyPath: "local_id", autoIncrement: true, index: "synced" },
        { name: "salecart", keyPath: "cart_row_id", autoIncrement: false },
        { name: "purchasecart", keyPath: "cart_row_id", autoIncrement: false },
        { name: "quotationcart", keyPath: "cart_row_id", autoIncrement: false }
      ];

      stores.forEach(storeConfig => {
        if (!db.objectStoreNames.contains(storeConfig.name)) {
          const store = db.createObjectStore(storeConfig.name, {
            keyPath: storeConfig.keyPath,
            autoIncrement: storeConfig.autoIncrement
          });
          if (storeConfig.index) {
            store.createIndex(storeConfig.index, storeConfig.index, { unique: false });
          }
        }
      });
    };

    req.onsuccess = (e) => {
      cachedDB = e.target.result;
      dbPromise = null;
      resolve(cachedDB);
    };

    req.onerror = (e) => {
      dbPromise = null;
      reject(e.target.error);
    };
  });

  return dbPromise;
}

// ── Generic CRUD Operations (Extremely Fast) ──

export async function addRecord(storeName, record) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.add(record);

    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
  });
}

export async function putRecord(storeName, record) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.put(record);

    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteRecord(storeName, key) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    store.delete(key);

    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}

export async function clearStore(storeName) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    store.clear();

    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}

export async function getAllRecords(storeName) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const store = tx.objectStore(storeName);
    const req = store.getAll();

    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
  });
}

export async function putRecordsBatch(storeName, records) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    records.forEach(rec => store.put(rec));

    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
}
