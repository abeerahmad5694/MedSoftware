const GlobalInlineModal = {
    config: null,
    currentConfig: null,
    items: [],
    selectedIndex: -1,
    
    /**
     * Initialize with an array of button configurations
     * @param {Array} configs - Array of { buttonSelector, targetSelectSelector, appLabel, modelName, label }
     */
    init(configs) {
        this.config = configs;
        this.setupEventListeners();
        
        // Move modal to body to ensure it centers on viewport and isn't trapped by parent CSS
        const modal = document.getElementById('globalInlineModal');
        if (modal && modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
    },
    
    setupEventListeners() {

        const closeBtn = document.getElementById('globalInlineModalClose');
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.close();
        });

        // Attach click listeners to configured buttons
        this.config.forEach(item => {
            const btns = document.querySelectorAll(item.buttonSelector);
            btns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.open(item);
                });
            });
        });
        
        // Search functionality removed per user request
        
        // Save on Enter
        document.getElementById('modalNewName')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.save();
            }
        });
        
        // Close on Escape key and handle Arrow navigation
        document.addEventListener('keydown', (e) => {
            const modal = document.getElementById('globalInlineModal');
            if (!modal || modal.classList.contains('hidden')) return;
            
            if (e.key === 'Escape') {
                this.close();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (this.selectedIndex < this.items.length - 1) {
                    this.selectedIndex++;
                    this.updateSelection();
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (this.selectedIndex > 0) {
                    this.selectedIndex--;
                    this.updateSelection();
                }
            }
        });
    },
    
    async open(itemConfig) {
        this.currentConfig = itemConfig;
        const modal = document.getElementById('globalInlineModal');
        const title = document.getElementById('modalTitle');
        const input = document.getElementById('modalNewName');
        const error = document.getElementById('modalError');
        
        // Reset UI
        title.innerText = `Manage ${itemConfig.label}`;
        this.newItem(); // Clears input, ID, and resets buttons
        
        error.classList.add('hidden');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        
        // Fetch data
        await this.fetchItems();
        input.focus();
    },
    
    close() {
        const modal = document.getElementById('globalInlineModal');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    },
    
    async fetchItems() {
        const tbody = document.getElementById('modalTableBody');
        const loading = document.getElementById('modalLoading');
        const empty = document.getElementById('modalEmptyState');
        
        tbody.innerHTML = '';
        loading.classList.remove('hidden');
        empty.classList.add('hidden');
        try {
            const url = `/${app_constants.global_inline_modal_lookup_api}/${this.currentConfig.appLabel}/${this.currentConfig.modelName}/`;
            const response = await fetch(url);
            const data = await response.json();
            loading.classList.add('hidden');
            if (data.results && data.results.length > 0) {
                this.items = data.results;
                this.renderTable(this.items);
                this.selectedIndex = -1; // Reset selection
            } else {
                this.items = [];
                empty.classList.remove('hidden');
            }
        } catch (err) {
            console.error('GlobalModal Fetch Error:', err);
            loading.innerText = 'Error loading items';
        }
    },
    
    renderTable(items) {
        const tbody = document.getElementById('modalTableBody');
        tbody.innerHTML = items.map((item, index) => `
            <tr data-index="${index}" class="cursor-pointer transition-colors group" onclick="GlobalInlineModal.selectedIndex = ${index}; GlobalInlineModal.updateSelection();" ondblclick="GlobalInlineModal.selectItem(${item.id}, '${item.name.replace(/'/g, "\\'")}')">
                <td class="px-3 py-1.5 text-[13px] text-gray-700 font-medium border-l-[3px] border-transparent group-hover:bg-blue-50/50">
                    <div class="flex items-center justify-between">
                        <span class="truncate pr-2">${item.name}</span>
                        <button class="text-gray-400 hover:text-blue-600 focus:outline-none p-1 rounded hover:bg-blue-100 transition-colors opacity-0 group-hover:opacity-100 flex items-center justify-center" onclick="event.stopPropagation(); GlobalInlineModal.editItem(${item.id || index}, '${item.name.replace(/'/g, "\\'")}')" title="Edit">
                            <i class="fas fa-edit text-[11px]"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        this.updateSelection();
    },
    
    updateSelection() {
        const rows = document.querySelectorAll('#modalTableBody tr');
        rows.forEach((row, index) => {
            const td = row.querySelector('td');
            const btn = row.querySelector('button');
            if (index === this.selectedIndex) {
                row.style.backgroundColor = '#003f92ff'; // bg-blue-50
                if (td) td.style.borderLeftColor = '#3b82f6'; // blue-500
                if (btn) btn.style.opacity = '1';
            } else {
                row.style.backgroundColor = 'transparent';
                if (td) td.style.borderLeftColor = 'transparent';
                if (btn) btn.style.opacity = '';
            }
        });
        
        if (this.selectedIndex >= 0 && rows[this.selectedIndex]) {
            rows[this.selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    },
    
    getMatchingConfigs(currentConfig) {
        if (!Array.isArray(this.config) || !currentConfig) return [];
        return this.config.filter(c => 
            c.appLabel === currentConfig.appLabel && 
            c.modelName === currentConfig.modelName
        );
    },

    selectItem(id, name) {
        if (this.currentConfig) {
            const matchingConfigs = this.getMatchingConfigs(this.currentConfig);

            matchingConfigs.forEach(cfg => {
                const selects = document.querySelectorAll(cfg.targetSelectSelector);
                const isCurrentTarget = cfg.targetSelectSelector === this.currentConfig.targetSelectSelector;

                selects.forEach(select => {
                    let optionExists = false;
                    Array.from(select.options).forEach(opt => {
                        if (String(opt.value) === String(id)) {
                            optionExists = true;
                            opt.text = name;
                        }
                    });

                    if (isCurrentTarget) {
                        if (!optionExists) {
                            const option = new Option(name, id, true, true);
                            select.add(option);
                        } else {
                            select.value = id;
                        }
                        select.dispatchEvent(new Event('change'));
                    } else {
                        if (!optionExists) {
                            const option = new Option(name, id, false, false);
                            select.add(option);
                        }
                    }
                });
            });
        }
        this.close();
    },
    
    editItem(id, name) {
        const input = document.getElementById('modalNewName');
        const idField = document.getElementById('modalItemId');
        const newBtn = document.getElementById('modalNewBtn');
        const saveBtn = document.getElementById('modalSaveBtn');
        const error = document.getElementById('modalError');
        
        input.value = name;
        if (idField) idField.value = id;
        
        if (newBtn) newBtn.classList.remove('hidden');
        if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-edit mr-1.5 text-[12px]"></i> Update';
        if (error) error.classList.add('hidden');
        
        input.focus();
    },
    
    newItem() {
        const input = document.getElementById('modalNewName');
        const idField = document.getElementById('modalItemId');
        const newBtn = document.getElementById('modalNewBtn');
        const saveBtn = document.getElementById('modalSaveBtn');
        const error = document.getElementById('modalError');
        
        if (input) input.value = '';
        if (idField) idField.value = '';
        
        if (newBtn) newBtn.classList.add('hidden');
        if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save mr-1.5 text-[12px]"></i> Save';
        if (error) error.classList.add('hidden');
        
        if (input) input.focus();
    },
    
    // Filter table function removed
    
    async save() {
        const input = document.getElementById('modalNewName');
        const btn = document.getElementById('modalSaveBtn');
        const error = document.getElementById('modalError');
        const idField = document.getElementById('modalItemId');
        
        const name = input.value.trim();
        const id = idField ? idField.value : '';
        
        if (!name) return;
        
        // UI State: Loading
        const isUpdate = !!id;
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin mr-1.5"></i> ${isUpdate ? 'Updating...' : 'Saving...'}`;
        error.classList.add('hidden');
        
        try {
            const url = `/${app_constants.global_inline_modal_lookup_api}/${this.currentConfig.appLabel}/${this.currentConfig.modelName}/`;
            const formData = new FormData();
            formData.append('name', name);
            if (id) {
                formData.append('id', id);
            }
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                            document.querySelector('meta[name="csrf-token"]')?.content;
            
            if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken);
            
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Success: Refresh list
                await this.fetchItems();
                
                // Reset to add mode
                this.newItem();
                
                // Update target select dropdown and any sibling dropdowns sharing the same model
                const matchingConfigs = this.getMatchingConfigs(this.currentConfig);
                
                matchingConfigs.forEach(cfg => {
                    const selects = document.querySelectorAll(cfg.targetSelectSelector);
                    const isCurrentTarget = cfg.targetSelectSelector === this.currentConfig.targetSelectSelector;
                    
                    selects.forEach(select => {
                        let optionExists = false;
                        Array.from(select.options).forEach(opt => {
                            if (String(opt.value) === String(data.id)) {
                                optionExists = true;
                                opt.text = data.name;
                            }
                        });
                        
                        if (isUpdate) {
                            if (isCurrentTarget) {
                                select.value = data.id;
                                select.dispatchEvent(new Event('change'));
                            }
                        } else {
                            if (!optionExists) {
                                // For the active target, select it; for others, add it without changing selection
                                const option = new Option(data.name, data.id, isCurrentTarget, isCurrentTarget);
                                select.add(option);
                            }
                            if (isCurrentTarget) {
                                select.value = data.id;
                                select.dispatchEvent(new Event('change'));
                            }
                        }
                    });
                });
                
            } else {
                error.innerText = data.error || 'Error saving item';
                error.classList.remove('hidden');
            }
        } catch (err) {
            console.error('GlobalModal Save Error:', err);
            error.innerText = 'Network error occurred';
            error.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            if (idField && idField.value) {
                btn.innerHTML = '<i class="fas fa-edit mr-1.5 text-[12px]"></i> Update';
            } else {
                btn.innerHTML = '<i class="fas fa-save mr-1.5 text-[12px]"></i> Save';
            }
        }
    }
};

// const inlinemodalCloseBtn = document.getElementById('globalInlineModalClose');
// inlinemodalCloseBtn?.addEventListener('click', (e) => {
//     e.preventDefault();
//     GlobalInlineModal.close();
// });

export default GlobalInlineModal;