/* ══════════════════════════════════════════════════════
   IndexedDB Configuration — globalsoft_db
   ══════════════════════════════════════════════════════ */

const db_name = 'globalsoft_db';
const DB_VERSION = 3;

// ── Store Registry ──
// Add new stores here and bump DB_VERSION to auto-create them.
const STORE_REGISTRY = {
    'inventory': { keyPath: 'inv_id' },
    'template_configs': { keyPath: 'key' }
};

const inventory_store = 'inventory';

const IndexDBConfig = {
    db: null,

    resolve_store_name: function (store_name) {
        if (!store_name) return inventory_store;
        if (STORE_REGISTRY[store_name]) return store_name;
        const lower = store_name.toLowerCase();
        if (STORE_REGISTRY[lower]) return lower;
        return store_name;
    },

    open_db: function (store_name = inventory_store) {
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(db_name, DB_VERSION);

            request.onupgradeneeded = function (event) {
                const db = event.target.result;
                // Recreate registered stores (handles keyPath changes on version bump)
                for (const [name, config] of Object.entries(STORE_REGISTRY)) {
                    if (db.objectStoreNames.contains(name)) {
                        db.deleteObjectStore(name);
                    }
                    db.createObjectStore(name, { keyPath: config.keyPath });
                }
            };

            request.onsuccess = function (event) {
                IndexDBConfig.db = event.target.result;
                resolve(IndexDBConfig.db);
            };

            request.onerror = function (event) {
                reject(event.target.error);
            };
        });
    },

    save_full_model: function (store_name = inventory_store, app_label, model_name) {
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise(async (resolve, reject) => {
            try {
                const data = await fetch_full_model(app_label, model_name);
                if (!data || !Array.isArray(data)) {
                    return reject("Invalid data received");
                }
                const db = await this.open_db(store_name);
                const transaction = db.transaction(store_name, "readwrite");
                const store = transaction.objectStore(store_name);

                store.clear();
                data.forEach(item => {
                    store.put(item);
                });

                transaction.oncomplete = function () {
                    resolve("success");
                };
                transaction.onerror = function (event) {
                    reject(event.target.error);
                };
            } catch (err) {
                console.error(err);
                reject(err);
            }
        });
    },

    /**
     * Get ALL records from a store. Used by GlobalSearchModal for local search.
     */
    get_all: function (store_name = inventory_store) {
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise(async (resolve, reject) => {
            try {
                const db = await this.open_db(store_name);
                const tx = db.transaction(store_name, 'readonly');
                const store = tx.objectStore(store_name);
                const request = store.getAll();
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            } catch (err) {
                reject(err);
            }
        });
    },

    /**
     * Get a single record by primary key from a store.
     */
    get_record: function (store_name, key) {
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise(async (resolve, reject) => {
            try {
                const db = await this.open_db(store_name);
                const tx = db.transaction(store_name, 'readonly');
                const store = tx.objectStore(store_name);
                const request = store.get(key);
                request.onsuccess = () => resolve(request.result || null);
                request.onerror = () => reject(request.error);
            } catch (err) {
                reject(err);
            }
        });
    },

    close_db: function (db) {
        db.close();
    },

    check_and_load_inventory: async function () {
        try {
            const db = await this.open_db();
            const transaction = db.transaction(inventory_store, "readonly");
            const store = transaction.objectStore(inventory_store);
            const countRequest = store.count();

            countRequest.onsuccess = () => {
                if (countRequest.result === 0 || true) {
                    // if (sessionStorage.getItem('inventory_fetched')) {
                    //     console.log("Inventory fetch already attempted this session. Skipping.");
                    //     return;
                    // }
                    sessionStorage.setItem('inventory_fetched', 'true');
                    console.log("Inventory not found in IndexDB. Fetching in background...");
                    setTimeout(() => {
                        this.save_full_model(inventory_store, 'inventory', 'Inventory')
                            .then(() => console.log("Inventory loaded into IndexDB successfully."))
                            .catch(err => console.error("Failed to load inventory into IndexDB:", err));
                    }, 500);
                } else {
                    console.log(`Inventory already in IndexDB (${countRequest.result} records). Skipping.`);
                }
            };

            countRequest.onerror = (err) => {
                console.error("Error counting inventory in IndexDB:", err);
            };
        } catch (err) {
            console.error("Error checking IndexDB:", err);
        }
    },

    reload_inventory: async function (btnElement = null) {
        
        let icon = null;
        if (btnElement) {
            icon = btnElement.querySelector('i');
            if (icon) icon.classList.add('fa-spin');
            btnElement.disabled = true;
        }
        try {
            console.log("Reloading inventory into IndexedDB...");
            await this.save_full_model(inventory_store, 'inventory', 'Inventory');
            localStorage.removeItem('inventory_Inventory_sync');
            console.log("Inventory successfully refreshed in IndexedDB.");
        } catch (err) {
            console.error("Failed to reload inventory into IndexedDB:", err);
            alert("Failed to refresh inventory: " + (err.message || err));
        } finally {
            if (btnElement) {
                if (icon) icon.classList.remove('fa-spin');
                btnElement.disabled = false;
            }
        }
    },

    save_update_record: function (store_name, record) {
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise(async (resolve, reject) => {
            try {
                const db = await this.open_db(store_name);
                const transaction = db.transaction(store_name, "readwrite");
                const store = transaction.objectStore(store_name);
                store.put(record);
                transaction.oncomplete = function () {
                    resolve("success");
                };
                transaction.onerror = function (event) {
                    reject(event.target.error);
                };
            } catch (err) {
                console.error(err);
                reject(err);
            }
        });
    },
    delete_record: function (store_name, record) {
        console.log('called')
        store_name = IndexDBConfig.resolve_store_name(store_name);
        return new Promise(async (resolve, reject) => {
            try {
                const db = await this.open_db(store_name);
                const transaction = db.transaction(store_name, "readwrite");
                const store = transaction.objectStore(store_name);
                store.delete(record);
                transaction.oncomplete = function () {
                    resolve("success");
                };
                transaction.onerror = function (event) {
                    reject(event.target.error);
                };
            } catch (err) {
                console.error(err);
                reject(err);
            }
        });
    },

    sync_indexdb: function (app_label, model_name) {
        const since = localStorage.getItem(`${app_label}_${model_name}_sync`) || '';
        let url = `/${app_constants.sync_indexdb_api}/${app_label}/${model_name}/`
        if(since != ''){
            url += '?since=' + since;
        }
        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error("Server error");
                return res.json();
            })
            .then(data => {
                if (data.success) {
                    data.results.forEach(item => {
                        this.save_update_record(model_name, item);
                    });
                    console.log('conso',data)
                    localStorage.setItem(`${app_label}_${model_name}_sync`, data.last_updated_at);
                }
            })
            .catch(err => console.error("Failed to sync indexdb:", err));
    }
};

window.IndexDBConfig = IndexDBConfig;