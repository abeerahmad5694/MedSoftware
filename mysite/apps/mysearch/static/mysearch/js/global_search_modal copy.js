/* ══════════════════════════════════════════════════════════════
   GlobalSearchModal — Production-Ready ERP Search Engine
   ══════════════════════════════════════════════════════════════
   Usage:
     GlobalSearchModal.init([{
         modalId: 'inventorySearch',
         triggerSelector: '#searchInventoryBtn',
         triggerKey: 'F3',                    // optional hotkey
         title: 'Find Product',
         placeholder: 'Search by name, barcode, ID...',
         appLabel: 'inventory',
         modelName: 'Inventory',
         primaryKey: 'inv_id',
         indexdbStore: 'inventory',            // null = skip local
         searchFields: ['prod_name','alias_name','barcode','manualbc','inv_id'],
         displayColumns: [
             { key: 'inv_id', header: 'ID', width: '80px' },
             { key: 'prod_name', header: 'Product Name' },
             { key: 'barcode', header: 'Barcode', width: '140px' },
             { key: 'base_price', header: 'Price', width: '100px' },
         ],
         excludeFilters: { active: false },   // exclude from local results
         pageSize: 50,
         onSelect: function(item) { }
     }]);
   ══════════════════════════════════════════════════════════════ */

import { ContantApi } from '/static/mysearch/js/app_constants.js';
const app_constants = new ContantApi();

/* ─────────────────────────────────────────────────────────────
   ModalStack — lightweight registry that tracks which modals
   are currently open so that:
   • The search modal overlay always sits above everything else.
   • Pressing Esc only closes the topmost modal.
   • Keyboard events (arrows, enter, page-up/down) are routed
     only to the topmost modal; lower modals are passivated.
   ───────────────────────────────────────────────────────────── */
const ModalStack = {
    _stack: [],          // array of { id, onEsc }

    push(id, onEsc) {
        // Remove if already present (re-open)
        this._stack = this._stack.filter(m => m.id !== id);
        this._stack.push({ id, onEsc });
    },

    pop(id) {
        this._stack = this._stack.filter(m => m.id !== id);
    },

    /** The topmost modal id, or null. */
    top() {
        return this._stack.length ? this._stack[this._stack.length - 1].id : null;
    },

    /** Is the given id the topmost modal? */
    isTop(id) {
        return this.top() === id;
    },

    /** Close the topmost modal (calls its onEsc callback). */
    closeTop() {
        if (!this._stack.length) return;
        const topModal = this._stack[this._stack.length - 1];
        if (topModal && typeof topModal.onEsc === 'function') {
            topModal.onEsc();
        }
    },
};

// Intercept Esc globally — only close the top modal.
// Using capture-phase so it fires before individual modal listeners.
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const top = ModalStack.top();
        // If search modal is on top, its own handler will deal with Esc;
        // for all other registered modals we call the onEsc callback.
        if (top && top !== 'gsm-overlay') {
            e.stopPropagation();
            ModalStack.closeTop();
        }
    }
}, true /* capture */);

/** Public helper — register any modal so Esc + stack work correctly.
 *  Call registerModal(elementOrId, onEscCallback) when you open a modal
 *  and unregisterModal(elementOrId) when you close it. */
window.ModalStack = ModalStack;

export const GlobalSearchModal = {

    _configs: {},
    _activeId: null,
    _state: null,
    _debounceTimer: null,
    _keydownBound: false,

    // ─── Init ───────────────────────────────────────────
    init(configs) {
        configs.forEach(cfg => {
            this._configs[cfg.modalId] = cfg;
        });
        this._attachTriggers();
        this._attachGlobalKeys();

        // Move modal to body for proper centering
        const overlay = document.getElementById('gsm-overlay');
        if (overlay && overlay.parentElement !== document.body) {
            document.body.appendChild(overlay);
        }
    },

    // ─── Trigger Buttons ────────────────────────────────
    _attachTriggers() {
        for (const [id, cfg] of Object.entries(this._configs)) {
            if (cfg.triggerSelector) {
                document.querySelectorAll(cfg.triggerSelector).forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.open(id);
                    });
                });
            }
        }
    },

    // ─── Global Keyboard ────────────────────────────────
    _attachGlobalKeys() {
        if (this._keydownBound) return;
        this._keydownBound = true;

        document.addEventListener('keydown', (e) => {
            // Hotkey triggers (F3, etc.) — only when search modal is NOT open
            if (!this._activeId) {
                for (const [id, cfg] of Object.entries(this._configs)) {
                    if (cfg.triggerKey && e.key === cfg.triggerKey) {
                        if (cfg.triggerInputId && e.target.id !== cfg.triggerInputId) {
                            continue;
                        }
                        e.preventDefault();
                        this.open(id);
                        return;
                    }
                }
                return; // nothing else to do when closed
            }

            // Navigation keys only apply when THIS modal is the topmost
            if (!ModalStack.isTop('gsm-overlay')) return;

            const s = this._state;

            switch (e.key) {
                case 'Escape':
                    e.preventDefault();
                    e.stopPropagation();
                    this.close();
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    if (s.selectedIndex < this._getPageItems().length - 1) {
                        s.selectedIndex++;
                        this._updateSelection();
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    if (s.selectedIndex > 0) {
                        s.selectedIndex--;
                        this._updateSelection();
                    }
                    break;
                case 'Enter':
                    e.preventDefault();
                    this._confirmSelection();
                    break;
                case 'PageDown':
                    e.preventDefault();
                    if (s.currentPage < s.totalPages) {
                        this.goToPage(s.currentPage + 1);
                    }
                    break;
                case 'PageUp':
                    e.preventDefault();
                    if (s.currentPage > 1) {
                        this.goToPage(s.currentPage - 1);
                    }
                    break;
            }
        });
    },

    // ─── Open ───────────────────────────────────────────
    async open(modalId) {
        const cfg = this._configs[modalId];
        if (!cfg) return console.error('GlobalSearchModal: config not found:', modalId);

        this._activeId = modalId;
        this._state = {
            allItems: [],
            filteredItems: [],
            pageItems: [],
            isLocalMode: false,
            selectedIndex: 0,
            currentPage: 1,
            totalPages: 1,
            totalCount: 0,
            query: '',
        };

        // Update UI
        const overlay = document.getElementById('gsm-overlay');
        const title = document.getElementById('gsm-title');
        const input = document.getElementById('gsm-search-input');

        title.textContent = cfg.title || 'Search';
        input.value = '';
        input.placeholder = cfg.placeholder || 'Search...';

        // Push to modal stack so Esc + z-index logic work correctly
        ModalStack.push('gsm-overlay', () => this.close());

        // Show modal
        overlay.style.display = '';
        overlay.setAttribute('aria-hidden', 'false');

        // Attach input listener (remove old first)
        input.removeEventListener('input', this._onInputBound);
        this._onInputBound = this._onInput.bind(this);
        input.addEventListener('input', this._onInputBound);

        // Show loading
        this._showLoading();

        // Try IndexedDB first
        if (cfg.indexdbStore) {
            try {
                const localData = await IndexDBConfig.get_all(cfg.indexdbStore);
                if (localData && localData.length > 0) {
                    this._state.allItems = this._applyExcludeFilters(localData, cfg);
                    this._state.isLocalMode = true;
                    this._state.totalCount = this._state.allItems.length;
                    this._localSearch('');
                    console.log(`GSM: Loaded ${this._state.allItems.length} items from IndexedDB [${cfg.indexdbStore}]`);
                    input.focus();
                    return;
                }
            } catch (err) {
                console.warn('GSM: IndexedDB failed, falling back to server:', err);
            }
        }

        // Fallback to server
        await this._serverFetch(1, '');
        input.focus();
    },

    // ─── Close ──────────────────────────────────────────
    close() {
        const overlay = document.getElementById('gsm-overlay');
        overlay.setAttribute('aria-hidden', 'true');
        setTimeout(() => { overlay.style.display = 'none'; }, 300);
        ModalStack.pop('gsm-overlay');
        this._activeId = null;
        this._state = null;
    },

    // ─── Exclude Filters (local) ────────────────────────
    _applyExcludeFilters(items, cfg) {
        if (!cfg.excludeFilters) return items;
        return items.filter(item => {
            for (const [key, val] of Object.entries(cfg.excludeFilters)) {
                if (item[key] === val) return false;
            }
            return true;
        });
    },

    // ─── Input Handler ──────────────────────────────────
    _onInput(e) {
        const query = e.target.value.trim();
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
            this._state.query = query;
            this._state.currentPage = 1;
            this._state.selectedIndex = 0;

            if (this._state.isLocalMode) {
                this._localSearch(query);
            } else {
                this._serverFetch(1, query);
            }
        }, 200);
    },

    // ─── Local Fuzzy Search ─────────────────────────────
    _localSearch(query) {
        const cfg = this._configs[this._activeId];
        const s = this._state;

        if (!query) {
            s.filteredItems = [...s.allItems];
        } else {
            const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
            s.filteredItems = s.allItems.filter(item => {
                return tokens.every(token => {
                    // Check primary key exact match for numeric tokens
                    if (/^\d+$/.test(token) && cfg.primaryKey) {
                        if (String(item[cfg.primaryKey]) === token) return true;
                    }
                    // Check all search fields for contains
                    return (cfg.searchFields || []).some(field => {
                        const val = item[field];
                        if (val === null || val === undefined) return false;
                        return String(val).toLowerCase().includes(token);
                    });
                });
            });
        }

        s.totalCount = s.filteredItems.length;
        s.totalPages = Math.max(1, Math.ceil(s.filteredItems.length / (cfg.pageSize || 15)));
        if (s.currentPage > s.totalPages) s.currentPage = 1;

        this._paginateAndRender();
    },

    // ─── Server Fetch ───────────────────────────────────
    async _serverFetch(page, query) {
        const cfg = this._configs[this._activeId];
        this._showLoading();

        try {
            const params = new URLSearchParams({
                q: query || '',
                page: page,
                page_size: cfg.pageSize || 15,
            });
            const url = `/${app_constants.global_search_api}/${cfg.appLabel}/${cfg.modelName}/?${params}`;
            const res = await fetch(url);
            const data = await res.json();

            if (data.success) {
                const s = this._state;
                s.pageItems = data.results;
                s.currentPage = data.page;
                s.totalPages = data.total_pages;
                s.totalCount = data.total_count;
                s.selectedIndex = 0;
                this._renderTable(s.pageItems, cfg);
                this._renderPagination();
                this._renderFooterInfo();
                this._updateSelection();
            } else {
                this._showEmpty(data.error || 'Search failed');
            }
        } catch (err) {
            console.error('GSM: Server fetch error:', err);
            this._showEmpty('Network error. Please try again.');
        }
    },

    // ─── Paginate Local + Render ─────────────────────────
    _paginateAndRender() {
        const cfg = this._configs[this._activeId];
        const s = this._state;
        const size = cfg.pageSize || 15;
        const start = (s.currentPage - 1) * size;
        s.pageItems = s.filteredItems.slice(start, start + size);

        this._renderTable(s.pageItems, cfg);
        this._renderPagination();
        this._renderFooterInfo();
        this._updateSelection();
    },

    // ─── Page Navigation ────────────────────────────────
    goToPage(page) {
        const s = this._state;
        if (page < 1 || page > s.totalPages) return;
        s.currentPage = page;
        s.selectedIndex = 0;

        if (s.isLocalMode) {
            this._paginateAndRender();
        } else {
            this._serverFetch(page, s.query);
        }
    },

    // ─── Get Current Page Items ─────────────────────────
    _getPageItems() {
        return this._state ? this._state.pageItems : [];
    },

    // ─── Confirm Selection (Enter / Click) ──────────────
    _confirmSelection() {
        const s = this._state;
        const items = this._getPageItems();
        if (s.selectedIndex >= 0 && s.selectedIndex < items.length) {
            this._selectItem(items[s.selectedIndex]);
        }
    },

    _selectItem(item) {
        const cfg = this._configs[this._activeId];
        if (cfg.onSelect && typeof cfg.onSelect === 'function') {
            cfg.onSelect(item);
        }
        this.close();
    },

    // ═══════════════════════════════════════════════════
    //  RENDERING
    // ═══════════════════════════════════════════════════

    _renderTable(items, cfg) {
        const container = document.getElementById('gsm-results');

        if (!items || items.length === 0) {
            this._showEmpty('No results found');
            return;
        }

        const cols = cfg.displayColumns || [];
        const query = (this._state.query || '').toLowerCase();
        const tokens = query ? query.split(/\s+/).filter(Boolean) : [];

        let html = '<table class="gsm-table"><thead><tr class="gsm-table-head-row">';
        cols.forEach(col => {
            const w = col.width ? ` style="width:${col.width}"` : '';
            html += `<th${w}>${col.header}</th>`;
        });
        html += '</tr></thead><tbody>';

        items.forEach((item, idx) => {
            html += `<tr class="result-row" data-index="${idx}" onclick="GlobalSearchModal._onRowClick(${idx})" ondblclick="GlobalSearchModal._onRowDblClick(${idx})">`;
            cols.forEach(col => {
                let val = item[col.key];
                if (val === null || val === undefined) val = '';
                let display = String(val);
                // Highlight matching tokens
                if (tokens.length > 0) {
                    display = this._highlightTokens(display, tokens);
                }
                html += `<td data-label="${col.header}">${display}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    },

    _highlightTokens(text, tokens) {
        if (!text) return '';
        let result = text;
        tokens.forEach(token => {
            if (!token) return;
            const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escaped})`, 'gi');
            result = result.replace(regex, '<mark>$1</mark>');
        });
        return result;
    },

    // ─── Pagination UI ──────────────────────────────────
    // Output: « 1 2 3 4 ... 199 200 »
    _renderPagination() {
        const s = this._state;
        const container = document.getElementById('gsm-pagination');
        if (s.totalPages <= 1) { container.innerHTML = ''; return; }

        const pages = this._getPaginationRange(s.currentPage, s.totalPages);
        let html = '';

        // Prev button
        html += `<button ${s.currentPage === 1 ? 'disabled' : ''} onclick="GlobalSearchModal.goToPage(${s.currentPage - 1})">«</button>`;

        pages.forEach(p => {
            if (p === '...') {
                html += `<button disabled>…</button>`;
            } else {
                const active = p === s.currentPage ? ' active' : '';
                html += `<button class="${active}" onclick="GlobalSearchModal.goToPage(${p})">${p}</button>`;
            }
        });

        // Next button
        html += `<button ${s.currentPage === s.totalPages ? 'disabled' : ''} onclick="GlobalSearchModal.goToPage(${s.currentPage + 1})">»</button>`;

        container.innerHTML = html;
    },

    _getPaginationRange(current, total) {
        if (total <= 9) {
            return Array.from({ length: total }, (_, i) => i + 1);
        }

        const pages = new Set();
        // First 4
        for (let i = 1; i <= Math.min(4, total); i++) pages.add(i);
        // Current area
        for (let i = Math.max(1, current - 1); i <= Math.min(total, current + 1); i++) pages.add(i);
        // Last 2
        pages.add(total - 1);
        pages.add(total);

        const sorted = [...pages].sort((a, b) => a - b);
        const result = [];
        for (let i = 0; i < sorted.length; i++) {
            if (i > 0 && sorted[i] - sorted[i - 1] > 1) result.push('...');
            result.push(sorted[i]);
        }
        return result;
    },

    // ─── Footer Info ────────────────────────────────────
    _renderFooterInfo() {
        const s = this._state;
        const el = document.getElementById('gsm-result-count');
        if (el) {
            const cfg = this._configs[this._activeId];
            const size = cfg.pageSize || 15;
            const start = (s.currentPage - 1) * size + 1;
            const end = Math.min(s.currentPage * size, s.totalCount);
            el.textContent = `${start}–${end} of ${s.totalCount}`;
        }
    },

    // ─── Selection Highlight ────────────────────────────
    _updateSelection() {
        const rows = document.querySelectorAll('#gsm-results .result-row');
        rows.forEach((row, idx) => {
            if (idx === this._state.selectedIndex) {
                row.classList.add('highlight');
                row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                row.classList.remove('highlight');
            }
        });
    },

    // ─── Row Click Handlers ─────────────────────────────
    _onRowClick(idx) {
        this._state.selectedIndex = idx;
        this._updateSelection();
    },

    _onRowDblClick(idx) {
        this._state.selectedIndex = idx;
        this._confirmSelection();
    },

    // ─── Loading / Empty States ─────────────────────────
    _showLoading() {
        document.getElementById('gsm-results').innerHTML =
            '<div class="loading-state"><div class="loading-spinner"></div><p>Loading...</p></div>';
        document.getElementById('gsm-pagination').innerHTML = '';
        const el = document.getElementById('gsm-result-count');
        if (el) el.textContent = '';
    },

    _showEmpty(msg) {
        document.getElementById('gsm-results').innerHTML =
            `<div class="no-results"><i class="fas fa-search" style="font-size:1.5rem;margin-bottom:8px;opacity:0.4"></i><p>${msg || 'No results found'}</p></div>`;
        document.getElementById('gsm-pagination').innerHTML = '';
        const el = document.getElementById('gsm-result-count');
        if (el) el.textContent = '0 results';
    },

    // ─── Programmatic Open (for external calls) ─────────
    openById(modalId) {
        this.open(modalId);
    }
};

window.GlobalSearchModal = GlobalSearchModal;

/* ── Reusable Search Utilities ──
   Exported for InlineSearchWidget and other consumers.
   These are pure functions — no modal DOM dependency. */

export function fuzzySearch(items, query, searchFields, primaryKey) {
    if (!query) return [...items];
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    return items.filter(item => {
        return tokens.every(token => {
            if (/^\d+$/.test(token) && primaryKey) {
                if (String(item[primaryKey]) === token) return true;
            }
            return (searchFields || []).some(field => {
                const val = item[field];
                if (val === null || val === undefined) return false;
                return String(val).toLowerCase().includes(token);
            });
        });
    });
}

export function highlightTokens(text, tokens) {
    if (!text) return '';
    let result = String(text);
    tokens.forEach(token => {
        if (!token) return;
        const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escaped})`, 'gi');
        result = result.replace(regex, '<mark>$1</mark>');
    });
    return result;
}

export function applyExcludeFilters(items, excludeFilters) {
    if (!excludeFilters) return items;
    return items.filter(item => {
        for (const [key, val] of Object.entries(excludeFilters)) {
            if (item[key] === val) return false;
        }
        return true;
    });
}
