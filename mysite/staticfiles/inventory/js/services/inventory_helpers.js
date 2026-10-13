// import { app_constants } from "/static/myglobal/js/app_constants.js";

class InventoryHelpers {
    fetchAndFillInventoryData = async function (inv_id) {
        const url = `/${window.app_constants.get_inventory_item_by_id || 'inventory/get_item_by_id'}/${inv_id}/`
        const response = await fetch(url)
        const data = await response.json()
        if(!response.ok){
            return alert(data.message || 'Some error occured while fetching the record')
        }
        if(data.success){
            this.fillInventoryData(data.data)
        }else{
            alert(data.message || 'Some error occured while fetching the record')
        }
    }
    fillInventoryData = function (data) {
        for (let field in data) {
            const element = document.getElementById(`id_${field}`)
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = !!data[field];
                } else {
                    element.value = data[field] !== null ? data[field] : '';
                }
            }
        }
    }
    
    saveUpdateInventory = async function () {
        const form = document.getElementById('inventoryForm');
        if (!form) return;

        const prodName = document.getElementById('id_prod_name')?.value?.trim();
        if (!prodName) {
            alert("Product Name is required");
            return;
        }

        const url = `/${window.app_constants.save_update_inventory || 'inventory/api/save_update_inventory'}`;
        const formData = new FormData(form);

        // Get CSRF Token
        let csrfToken = '';
        const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            csrfToken = csrfInput.value;
        } else {
            const match = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
            csrfToken = match ? match.split('=')[1] : '';
        }

        try {
            const saveBtn = document.getElementById('inventory_save_btn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin text-[10px]"></i> SAVING...';
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            const resData = await response.json();

            if (response.ok && resData.success) {
                alert(resData.message || "Saved successfully!");

                if (resData.data) {
                    this.fillInventoryData(resData.data);
                }

                if (resData.db_record && window.IndexDBConfig) {
                    try {
                        await window.IndexDBConfig.save_update_record('inventory', resData.db_record);
                        console.log("IndexedDB updated:", resData.db_record);
                    } catch (idbErr) {
                        console.error("Failed to update IndexedDB:", idbErr);
                    }
                }
            } else {
                if (resData.errors) {
                    const errorMsg = Object.entries(resData.errors)
                        .map(([field, err]) => `${field.toUpperCase()}: ${err}`)
                        .join('\n');
                    alert("Validation Error:\n" + errorMsg);
                } else {
                    alert("Error: " + (resData.error || "Failed to save inventory"));
                }
            }
        } catch (err) {
            console.error("Network error saving inventory:", err);
            alert("Network error: Could not save inventory.");
        } finally {
            const saveBtn = document.getElementById('inventory_save_btn');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-save text-[10px]"></i> SAVE ITEM (F2)';
            }
        }
    }

    resetForm = function () {
        const form = document.getElementById('inventoryForm');
        if (form) {
            form.reset();
            const invIdEl = document.getElementById('id_inv_id');
            if (invIdEl) invIdEl.value = '';
        }
    }

    deleteInventoryItem = async function () {
        const inv_id = document.getElementById('id_inv_id')?.value;
        if (!inv_id) return alert('No record found to delete');

        const url = `/${window.app_constants.delete_inventory_item || 'inventory/api/delete_inventory_item'}/${inv_id}/`;

        // Get CSRF Token
        let csrfToken = '';
        const form = document.getElementById('inventoryForm');
        if (form) {
            const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfInput) {
                csrfToken = csrfInput.value;
            }
        }
        if (!csrfToken) {
            const match = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
            csrfToken = match ? match.split('=')[1] : '';
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                return alert(errData.error || 'Some error occured while deleting the record');
            }

            // 1. Delete from IndexedDB
            // if (window.IndexDBConfig) {
            //     await window.IndexDBConfig.delete_record('inventory', parseInt(inv_id));
            //     console.log('Deleted from IndexedDB:', inv_id);
            // }

            const data = await response.json();
            if (data.success) {
                if (window.IndexDBConfig) {
                    await window.IndexDBConfig.delete_record('inventory', parseInt(inv_id));
                }
                alert(data.message);
                this.resetForm();
                window.location.reload();
            } else {
                return alert(data.message);
            }
        } catch (err) {
            console.error("Network error deleting inventory:", err);
            alert("Network error: Could not delete inventory item.");
        }
    }

    copySameItem = async function () {
        const inv_id = document.getElementById('id_inv_id')?.value;
        if (!inv_id) return alert('No record found to copy');
        document.getElementById('id_inv_id').value = '';
        alert(` ${inv_id}! Data Copied Successfully`)
    }
}

const InvHelpers = new InventoryHelpers()
export default InvHelpers;