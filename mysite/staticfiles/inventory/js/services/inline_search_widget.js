/* ══════════════════════════════════════════════════════════════
   InlineSearchWidget — Embedded live search panel
   ──────────────────────────────────────────────────────────────
   Reuses fuzzySearch / highlightTokens / applyExcludeFilters
   from GlobalSearchModal. Renders inline (not a modal).
   
   Supports:
     • Live search with debounce
     • Arrow key ↑↓ navigation
     • Enter to select / Double-click to select
     • Token highlighting in results
   ══════════════════════════════════════════════════════════════ */

import { fuzzySearch, highlightTokens, applyExcludeFilters } from '/static/mysearch/js/global_search_modal.js';

export class InlineSearchWidget {

    constructor(config) {
        this.cfg = {
            containerId: config.containerId,
            inputId: config.inputId,
            resultsId: config.resultsId,
            countId: config.countId || null,

            indexdbStore: config.indexdbStore || 'inventory',
            searchFields: config.searchFields || [],
            primaryKey: config.primaryKey || 'inv_id',
            displayColumns: config.displayColumns || [],
            excludeFilters: config.excludeFilters || null,
            pageSize: config.pageSize || 15,

            onSelect: config.onSelect || function () {},
        };

        this._allItems = [];
        this._filteredItems = [];
        this._pageItems = [];
        this._selectedIndex = 0;
        this._debounceTimer = null;

        this._init();
    }

    /* ── Bootstrap ─────────────────────────────────────── */
    async _init() {
        this._bindInput();
        this._bindKeyboard();
        await this._loadData();
    }

    /* ── Load from IndexedDB ──────────────────────────── */
    async _loadData() {
        const resultsEl = document.getElementById(this.cfg.resultsId);
        if (!resultsEl) return;

        resultsEl.innerHTML = '<div class="isw-loading"><div class="isw-spinner"></div></div>';

        try {
            if (window.IndexDBConfig) {
                const data = await window.IndexDBConfig.get_all(this.cfg.indexdbStore);
                if (data && data.length > 0) {
                    this._allItems = applyExcludeFilters(data, this.cfg.excludeFilters);
                    this._search('');
                    return;
                }
            }
        } catch (err) {
            console.warn('InlineSearchWidget: IndexedDB load failed:', err);
        }
        this._showEmpty('No data available');
    }

    /* ── Input Binding ────────────────────────────────── */
    _bindInput() {
        const input = document.getElementById(this.cfg.inputId);
        if (!input) return;

        input.addEventListener('input', () => {
            clearTimeout(this._debounceTimer);
            this._debounceTimer = setTimeout(() => {
                this._selectedIndex = 0;
                this._search(input.value.trim());
            }, 150);
        });
    }

    /* ── Keyboard Navigation ──────────────────────────── */
    _bindKeyboard() {
        const input = document.getElementById(this.cfg.inputId);
        if (!input) return;

        input.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (this._selectedIndex < this._pageItems.length - 1) {
                        this._selectedIndex++;
                        this._updateSelection();
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    if (this._selectedIndex > 0) {
                        this._selectedIndex--;
                        this._updateSelection();
                    }
                    break;
                case 'Enter':
                    e.preventDefault();
                    this._confirmSelection();
                    break;
            }
        });
    }

    /* ── Core Search (delegates to GlobalSearchModal util) ── */
    _search(query) {
        this._filteredItems = fuzzySearch(
            this._allItems,
            query,
            this.cfg.searchFields,
            this.cfg.primaryKey
        );

        // Paginate
        this._pageItems = this._filteredItems.slice(0, this.cfg.pageSize);
        this._renderResults(query);
        this._updateCount();
        this._updateSelection();
    }

    /* ── Render Results ───────────────────────────────── */
    _renderResults(query) {
        const container = document.getElementById(this.cfg.resultsId);
        if (!container) return;

        if (!this._pageItems || this._pageItems.length === 0) {
            this._showEmpty(query ? 'No matches found' : 'No items');
            return;
        }

        const cols = this.cfg.displayColumns;
        const tokens = query ? query.toLowerCase().split(/\s+/).filter(Boolean) : [];

        let html = '<table class="isw-table"><thead><tr>';
        cols.forEach(col => {
            const w = col.width ? ` style="width:${col.width}"` : '';
            html += `<th${w}>${col.header}</th>`;
        });
        html += '</tr></thead><tbody>';

        this._pageItems.forEach((item, idx) => {
            html += `<tr class="isw-row" data-index="${idx}">`;
            cols.forEach(col => {
                let val = item[col.key];
                if (val === null || val === undefined) val = '';
                let display = String(val);
                if (tokens.length > 0) {
                    display = highlightTokens(display, tokens);
                }
                html += `<td>${display}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;

        // Bind click/dblclick
        container.querySelectorAll('.isw-row').forEach(row => {
            const idx = parseInt(row.dataset.index);
            row.addEventListener('click', () => {
                this._selectedIndex = idx;
                this._updateSelection();
            });
            row.addEventListener('dblclick', () => {
                this._selectedIndex = idx;
                this._confirmSelection();
            });
        });
    }

    /* ── Selection Highlight ──────────────────────────── */
    _updateSelection() {
        const container = document.getElementById(this.cfg.resultsId);
        if (!container) return;

        const rows = container.querySelectorAll('.isw-row');
        rows.forEach((row, idx) => {
            if (idx === this._selectedIndex) {
                row.classList.add('isw-highlight');
                row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                row.classList.remove('isw-highlight');
            }
        });
    }

    /* ── Confirm Selection ────────────────────────────── */
    _confirmSelection() {
        if (this._selectedIndex >= 0 && this._selectedIndex < this._pageItems.length) {
            const item = this._pageItems[this._selectedIndex];
            if (this.cfg.onSelect && typeof this.cfg.onSelect === 'function') {
                this.cfg.onSelect(item);
            }
        }
    }

    /* ── Count Badge ──────────────────────────────────── */
    _updateCount() {
        if (!this.cfg.countId) return;
        const el = document.getElementById(this.cfg.countId);
        if (el) {
            const showing = Math.min(this._pageItems.length, this._filteredItems.length);
            el.textContent = `${showing} of ${this._allItems.length}`;
        }
    }

    /* ── Empty / Loading States ────────────────────────── */
    _showEmpty(msg) {
        const container = document.getElementById(this.cfg.resultsId);
        if (!container) return;
        container.innerHTML = `<div class="isw-empty"><i class="fas fa-box-open"></i><span>${msg}</span></div>`;
    }

    /* ── Reload data (call after save/delete to refresh) ── */
    async refresh() {
        await this._loadData();
    }
}
