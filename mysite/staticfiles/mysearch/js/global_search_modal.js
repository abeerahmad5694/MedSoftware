/* ══════════════════════════════════════════════════════════════
   GlobalSearchModal — Production-Ready ERP Search Engine
   ══════════════════════════════════════════════════════════════
   Usage:
     GlobalSearchModal.init([{
         modalId: 'inventorySearch',
         triggerSelector: '#searchInventoryBtn',
         triggerKey: 'F3',
         title: 'Find Product',
         placeholder: 'Search by name, barcode, ID...',
         appLabel: 'inventory',
         modelName: 'Inventory',
         primaryKey: 'inv_id',
         indexdbStore: 'inventory',
         searchFields: ['prod_name','alias_name','barcode','manualbc','inv_id'],
         displayColumns: [
             { key: 'inv_id', header: 'ID', width: '80px' },
             { key: 'prod_name', header: 'Product Name' },
             { key: 'barcode', header: 'Barcode', width: '140px' },
             { key: 'base_price', header: 'Price', width: '100px' },
         ],
         excludeFilters: { active: false },
         pageSize: 50,
         onSelect: function(item) { }
     }]);
   ══════════════════════════════════════════════════════════════ */

import { ContantApi } from '/static/mysearch/js/app_constants.js';
const app_constants = new ContantApi();

/* ══════════════════════════════════════════════════════════════
   DEFAULT_SEARCH_REGISTRY
   Mirrors the Django backend registry exactly.
   Key format: "appLabel.ModelName"  →  e.g. "inventory.Inventory"
   ══════════════════════════════════════════════════════════════ */
const DEFAULT_SEARCH_REGISTRY = {
    'inventory.Inventory': {
        primary_key: 'inv_id',
        searchFields: ['prod_name','alias_name','barcode','manualbc','barcode2','inv_id'],
        displayColumns: [
            { key: 'inv_id',     header: 'ID',           width: '80px'  },
            { key: 'prod_name',  header: 'Product Name'                 },
            { key: 'barcode',    header: 'Barcode',       width: '140px' },
            { key: 'base_price', header: 'Price',         width: '100px' },
        ],
        pageSize: 50,
        excludeFilters: {'is_deleted':false},
        pipelines: [
            {
                id: 'numeric',
                condition: (q) => /^\d+$/.test(q),
                rules: [
                    { if: (q) => q.length <= 6, field: 'inv_id',   lookup: 'exact', rank: 100, stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'barcode',  lookup: 'exact', rank: 100, stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'barcode2', lookup: 'exact', rank:  95, stop_if_found: true },
                    { if: (q) => q.length >= 5, field: 'manualbc', lookup: 'exact', rank:  90, stop_if_found: true },
                ]
            },
            {
                id: 'string',
                condition: (q) => true,
                rules: [
                    { field: 'manualbc',   lookup: 'exact',     rank: 100, stop_if_found: true },
                    { field: 'barcode2',   lookup: 'exact',     rank:  90, stop_if_found: true },
                    { field: 'alias_name', lookup: 'exact',     rank:  80, stop_if_found: true },
                    { field: 'barcode',    lookup: 'exact',     rank:  70, stop_if_found: true },
                    { field: 'prod_name',  lookup: 'token_and', rank:  50 },
                    { field: 'alias_name', lookup: 'token_and', rank:  40 },
                ]
            }
        ]
    },

    'myaccounts.Accounts': {
        primary_key: 'ACC_CODE',
        searchFields: ['ACC_CODE','ACC_NAME'],
        displayColumns: [
            { key: 'ACC_CODE', header: 'ACC_CODE' },
            { key: 'ACC_NAME', header: 'ACC_NAME' },
        ],
        pageSize: 50,
        excludeFilters: {},
        pipelines: [
            {
                condition: () => true,
                rules: [
                    { field: 'ACC_CODE', lookup: 'exact',     rank: 100, stop_if_found: true },
                    { field: 'ACC_NAME', lookup: 'token_and', rank:  50 },
                ]
            }
        ]
    }
};

/* ══════════════════════════════════════════════════════════════
   _mergeConfig(userCfg) → finalConfig
   Merges user-supplied config with DEFAULT_SEARCH_REGISTRY.
   User values always win. Never throws.
   ══════════════════════════════════════════════════════════════ */
function _mergeConfig(userCfg) {
    const key = `${userCfg.appLabel}.${userCfg.modelName}`;
    const reg = DEFAULT_SEARCH_REGISTRY[key] || null;

    const fallbackReg = {
        primary_key:    userCfg.primaryKey || userCfg.primary_key || 'id',
        searchFields:   userCfg.searchFields   || [],
        displayColumns: userCfg.displayColumns || [],
        pageSize:       50,
        excludeFilters: {},
        pipelines: [{
            condition: () => true,
            rules: (userCfg.searchFields || []).map(f => ({ field: f, lookup: 'token_and', rank: 50 }))
        }]
    };

    const base = reg || fallbackReg;

    return {
        ...base,
        ...userCfg,
        primary_key:    userCfg.primaryKey  || userCfg.primary_key  || base.primary_key,
        searchFields:   userCfg.searchFields   || base.searchFields,
        displayColumns: userCfg.displayColumns || base.displayColumns,
        pageSize:       userCfg.pageSize       || base.pageSize,
        excludeFilters: (userCfg.excludeFilters !== undefined)
                            ? userCfg.excludeFilters
                            : base.excludeFilters,
        pipelines:      userCfg.pipelines      || base.pipelines,
    };
}

/* ══════════════════════════════════════════════════════════════
   LocalSearchEngine
   ══════════════════════════════════════════════════════════════
   • load(items)  — filter via excludeFilters, build O(1) exact
                    inverted indexes once.
   • search(q)    — pipeline-driven:
                    exact  → O(1) Map.get()
                    fuzzy  → O(n) early-exit token_and
   ══════════════════════════════════════════════════════════════ */
class LocalSearchEngine {

    constructor(cfg) {
        this._cfg      = cfg;
        this._allItems = [];
        this._indexes  = {};      // field → Map<lowerValue, item[]>
        this._byPK     = new Map();
        this._ready    = false;
    }

    /** Load items and build indexes. Call once per store. */
    async load(items) {
        const t0  = performance.now();
        const cfg = this._cfg;

        // Apply excludeFilters up-front so indexes never contain excluded items
        this._allItems = _applyExcludeFilters(items, cfg.excludeFilters || {});

        // Primary-key lookup map
        this._byPK.clear();
        const pk = cfg.primary_key || cfg.primaryKey;
        for (const item of this._allItems) {
            this._byPK.set(String(item[pk]).toLowerCase(), item);
        }

        // Collect fields that need exact-match inverted index
        const exactFields = new Set();
        for (const pipeline of (cfg.pipelines || [])) {
            for (const rule of (pipeline.rules || [])) {
                if (rule.lookup === 'exact') exactFields.add(rule.field);
            }
        }

        // Build Map<lowerValue → item[]> per field  O(n·|exactFields|)
        this._indexes = {};
        for (const field of exactFields) {
            const map = new Map();
            for (const item of this._allItems) {
                const raw = item[field];
                if (raw === null || raw === undefined) continue;
                const key = String(raw).toLowerCase();
                if (!map.has(key)) map.set(key, []);
                map.get(key).push(item);
            }
            this._indexes[field] = map;
        }

        this._ready = true;
        console.log(
            `GSM LocalSearchEngine: indexed ${this._allItems.length} items, ` +
            `${exactFields.size} exact fields in ${(performance.now() - t0).toFixed(1)}ms`
        );
    }


    _levenshtein(a, b) {
        if (a === b) return 0;
        const al = a.length, bl = b.length;
        if (al === 0) return bl;
        if (bl === 0) return al;
        // early exit if length diff > 2 - not a typo
        if (Math.abs(al - bl) > 2) return 3;

        const dp = Array(bl + 1).fill(0).map((_, i) => i);
        for (let i = 1; i <= al; i++) {
            let prev = dp[0];
            dp[0] = i;
            for (let j = 1; j <= bl; j++) {
                const cur = dp[j];
                const cost = a[i-1] === b[j-1]? 0 : 1;
                dp[j] = Math.min(
                    dp[j] + 1, // deletion
                    dp[j-1] + 1, // insertion
                    prev + cost // substitution
                );
                prev = cur;
            }
        }
        return dp[bl];
    }

    _isFuzzyMatch(token, word) {
        // wy -> way = subsequence match
        if (token.length <= 3) {
            let ti = 0;
            for (let wi = 0; wi < word.length && ti < token.length; wi++) {
                if (word[wi] === token[ti]) ti++;
            }
            return ti === token.length;
        }
        // panl -> panel = 1 edit distance
        // panal -> panel = 1 substitution
        if (word.includes(token)) return true;
        if (token.length <= 5) return this._levenshtein(token, word) <= 1;
        return this._levenshtein(token, word) <= 2;
    }



    /** Public search entry point. Returns { items, elapsed }. */
    search(query) {
        const t0 = performance.now();
        const results = query ? this._runPipelines(query) : [...this._allItems];
        const elapsed = (performance.now() - t0).toFixed(2);
        console.log(`GSM search("${query}"): ${results.length} results in ${elapsed}ms`);
        return { items: results, elapsed };
    }

    /**
     * Tokenize query.
     * "wy+panel"   → ["wy","panel"]
     * "02=010=12"  → ["02","010","12"]
     */
    _tokenize(query) {
        return query.toLowerCase()
            .replace(/[^a-z0-9]+/g, ' ')
            .split(' ')
            .filter(Boolean);
    }

    /**
     * Token-AND match for a single field value.
     *
     * Short token (len ≤ 3): ALL chars of token must appear in text.
     *   "wy" matches "WAY"  because 'w' ∈ "way"  and 'y' ∈ "way". ✓
     *   "02" matches "02=010=12 WAY…" because '0','2' ∈ text. ✓
     *
     * Longer token: substring match.
     *   "panel" matches "WAY PANEL SR" because "panel" ⊆ "way panel sr". ✓
     *
     * ALL tokens must pass (AND logic).
     */
    _matchTokenAnd(text, tokens) {
        if (!text) return false;
        const lower = String(text).toLowerCase();
        const words = lower.split(/[^a-z0-9]+/).filter(Boolean);
        if (words.length === 0) return false;

        for (const token of tokens) {
            let found = false;
            // check exact substring first - fastest O(1)
            if (lower.includes(token)) {
                found = true;
            } else {
                // check each word for fuzzy
                for (const w of words) {
                    if (this._isFuzzyMatch(token, w)) { found = true; break; }
                }
                // also check 2-word combo for "waypanel" vs "way panel"
                if (!found && token.length >= 4) {
                    for (let i = 0; i < words.length - 1; i++) {
                        const combined = words[i] + words[i+1];
                        if (this._levenshtein(token, combined) <= 2) { found = true; break; }
                    }
                }
            }
            if (!found) return false; // AND logic - all tokens must match
        }
        return true;
    }

    /** O(n) fuzzy filter over all items for one field, with early exit. */
    _fuzzyFilter(field, tokens, limit) {
        const results = [];
        for (const item of this._allItems) {
            if (this._matchTokenAnd(item[field], tokens)) {
                results.push(item);
                if (results.length >= limit) break;
            }
        }
        return results;
    }

    /** Pipeline executor — returns ranked, deduped items[]. */
    _runPipelines(query) {
        const cfg      = this._cfg;
        const pipelines = cfg.pipelines || [];
        const pageSize  = cfg.pageSize  || 50;
        const tokens    = this._tokenize(query);
        const qLower    = query.toLowerCase().trim();
        const pk        = cfg.primary_key || cfg.primaryKey;

        // pkValue → { item, rank }  (dedup + best-rank wins)
        const seen = new Map();

        const merge = (candidates, rank) => {
            for (const item of candidates) {
                const pkVal = String(item[pk]);
                const prev  = seen.get(pkVal);
                if (!prev || prev.rank < rank) seen.set(pkVal, { item, rank });
            }
        };

        for (const pipeline of pipelines) {
            if (typeof pipeline.condition === 'function' && !pipeline.condition(query)) continue;

            let stoppedEarly = false;

            for (const rule of (pipeline.rules || [])) {
                if (typeof rule.if === 'function' && !rule.if(query)) continue;

                let candidates = [];

                if (rule.lookup === 'exact') {
                    const idx = this._indexes[rule.field];
                    if (idx) candidates = idx.get(qLower) || [];

                } else if (rule.lookup === 'token_and') {
                    const remaining = pageSize - seen.size;
                    if (remaining > 0) {
                        candidates = this._fuzzyFilter(rule.field, tokens, remaining + 10);
                    }
                }

                merge(candidates, rule.rank);

                if (candidates.length > 0 && rule.stop_if_found) {
                    stoppedEarly = true;
                    break;
                }
            }

            if (stoppedEarly) break;
        }

        return [...seen.values()]
            .sort((a, b) => b.rank - a.rank)
            .map(e => e.item)
            .slice(0, pageSize);
    }

    get ready()      { return this._ready; }
    get totalItems() { return this._allItems.length; }
}

/* ── Shared helper (engine + modal) ── */
function _applyExcludeFilters(items, excludeFilters) {
    if (!excludeFilters || Object.keys(excludeFilters).length === 0) return items;
    return items.filter(item => {
        for (const [key, val] of Object.entries(excludeFilters)) {
            if (item[key] === val) return false;
        }
        return true;
    });
}

/* ─────────────────────────────────────────────────────────────
   ModalStack — lightweight registry that tracks open modals so:
   • Esc only closes the topmost modal.
   • Keyboard events route only to the topmost modal.
   ───────────────────────────────────────────────────────────── */
const ModalStack = {
    _stack: [],

    push(id, onEsc) {
        this._stack = this._stack.filter(m => m.id !== id);
        this._stack.push({ id, onEsc });
    },

    pop(id) {
        this._stack = this._stack.filter(m => m.id !== id);
    },

    top() {
        return this._stack.length ? this._stack[this._stack.length - 1].id : null;
    },

    isTop(id) { return this.top() === id; },

    closeTop() {
        if (!this._stack.length) return;
        const top = this._stack[this._stack.length - 1];
        if (top && typeof top.onEsc === 'function') top.onEsc();
    },
};

// Global Esc — only close the topmost modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const top = ModalStack.top();
        if (top && top !== 'gsm-overlay') {
            e.stopPropagation();
            ModalStack.closeTop();
        }
    }
}, true);

window.ModalStack = ModalStack;

/* ══════════════════════════════════════════════════════════════
   GlobalSearchModal
   ══════════════════════════════════════════════════════════════ */
export const GlobalSearchModal = {

    _configs:       {},   // modalId → mergedConfig
    _engines:       {},   // modalId → LocalSearchEngine
    _activeId:      null,
    _state:         null,
    _debounceTimer: null,
    _keydownBound:  false,

    /* ─────────────────────────────────────────────────────
       init(configs)
       • Merges each userCfg with DEFAULT_SEARCH_REGISTRY.
       • Eagerly loads IndexedDB into LocalSearchEngine.
       • Binds trigger buttons and hotkeys.
    ───────────────────────────────────────────────────── */
    async init(configs) {
        for (const userCfg of configs) {
            const cfg = _mergeConfig(userCfg);
            this._configs[cfg.modalId] = cfg;

            if (cfg.indexdbStore) {
                const engine = new LocalSearchEngine(cfg);
                this._engines[cfg.modalId] = engine;

                // Non-blocking eager pre-load
                IndexDBConfig.get_all(cfg.indexdbStore)
                    .then(data => {
                        if (data && data.length > 0) {
                            engine.load(data);
                            console.log(`GSM: Engine ready [${cfg.modalId}] — ${data.length} rows`);
                        } else {
                            console.warn(`GSM: No data in IndexedDB store "${cfg.indexdbStore}"`);
                        }
                    })
                    .catch(err => console.warn(`GSM: IndexedDB load failed [${cfg.modalId}]:`, err));
            }
        }

        this._attachTriggers();
        this._attachGlobalKeys();

        const overlay = document.getElementById('gsm-overlay');
        if (overlay && overlay.parentElement !== document.body) {
            document.body.appendChild(overlay);
        }
    },

    /* ─────────────────────────────────────────────────────
       search(modalId, query) — public / testable
       Returns items[] synchronously from the pre-built engine.

       Test cases:
         GlobalSearchModal.search('inventorySearch', '123')
         GlobalSearchModal.search('inventorySearch', 'wy panel')
    ───────────────────────────────────────────────────── */
    search(modalId, query) {
        const engine = this._engines[modalId];
        if (!engine || !engine.ready) {
            console.warn(`GSM.search: engine not ready for [${modalId}]`);
            return [];
        }
        return engine.search(query).items;
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
            if (!this._activeId) {
                for (const [id, cfg] of Object.entries(this._configs)) {
                    if (cfg.triggerKey && e.key === cfg.triggerKey) {
                        if (cfg.triggerInputId && e.target.id !== cfg.triggerInputId) continue;
                        e.preventDefault();
                        this.open(id);
                        return;
                    }
                }
                return;
            }

            if (!ModalStack.isTop('gsm-overlay')) return;

            const s = this._state;
            switch (e.key) {
                case 'Escape':
                    e.preventDefault(); e.stopPropagation();
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
                    if (s.currentPage < s.totalPages) this.goToPage(s.currentPage + 1);
                    break;
                case 'PageUp':
                    e.preventDefault();
                    if (s.currentPage > 1) this.goToPage(s.currentPage - 1);
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
            allItems: [], filteredItems: [], pageItems: [],
            isLocalMode: false, selectedIndex: 0,
            currentPage: 1, totalPages: 1, totalCount: 0, query: '',
        };

        const overlay = document.getElementById('gsm-overlay');
        const title   = document.getElementById('gsm-title');
        const input   = document.getElementById('gsm-search-input');

        title.textContent = cfg.title       || 'Search';
        input.value       = '';
        input.placeholder = cfg.placeholder || 'Search...';

        ModalStack.push('gsm-overlay', () => this.close());
        overlay.style.display = '';
        overlay.setAttribute('aria-hidden', 'false');

        input.removeEventListener('input', this._onInputBound);
        this._onInputBound = this._onInput.bind(this);
        input.addEventListener('input', this._onInputBound);

        this._showLoading();

        // ── Use pre-built engine if ready ─────────────────
        const engine = this._engines[modalId];
        if (engine && engine.ready) {
            this._state.isLocalMode = true;
            this._state.totalCount  = engine.totalItems;
            this._localSearch('');
            input.focus();
            return;
        }

        // ── On-demand load (engine not ready yet) ──────────
        if (cfg.indexdbStore) {
            try {
                const localData = await IndexDBConfig.get_all(cfg.indexdbStore);
                if (localData && localData.length > 0) {
                    const eng = engine || new LocalSearchEngine(cfg);
                    if (!engine) this._engines[modalId] = eng;
                    await eng.load(localData);
                    this._state.isLocalMode = true;
                    this._state.totalCount  = eng.totalItems;
                    this._localSearch('');
                    console.log(`GSM: Loaded ${localData.length} items [${cfg.indexdbStore}]`);
                    input.focus();
                    return;
                }
            } catch (err) {
                console.warn('GSM: IndexedDB failed, falling back to server:', err);
            }
        }

        // ── Server fallback ────────────────────────────────
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
        this._state    = null;
    },

    // ─── Input Handler ──────────────────────────────────
    _onInput(e) {
        const query = e.target.value.trim();
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
            this._state.query         = query;
            this._state.currentPage   = 1;
            this._state.selectedIndex = 0;
            if (this._state.isLocalMode) this._localSearch(query);
            else                         this._serverFetch(1, query);
        }, 200);
    },

    // ─── Local Search (pipeline-driven via LocalSearchEngine) ──
    _localSearch(query) {
        const cfg    = this._configs[this._activeId];
        const s      = this._state;
        const engine = this._engines[this._activeId];

        let results;
        if (engine && engine.ready) {
            results = engine.search(query).items;
        } else {
            // Bare fallback — should rarely be reached
            results = _bareSearch(query, s.allItems || [], cfg);
        }

        s.filteredItems = results;
        s.totalCount    = results.length;
        s.totalPages    = Math.max(1, Math.ceil(results.length / (cfg.pageSize || 50)));
        if (s.currentPage > s.totalPages) s.currentPage = 1;

        this._paginateAndRender();
    },

    // ─── Server Fetch ───────────────────────────────────
    async _serverFetch(page, query) {
        const cfg = this._configs[this._activeId];
        this._showLoading();
        try {
            const params = new URLSearchParams({
                q: query || '', page, page_size: cfg.pageSize || 15,
            });
            const url  = `/${app_constants.global_search_api}/${cfg.appLabel}/${cfg.modelName}/?${params}`;
            const res  = await fetch(url);
            const data = await res.json();

            if (data.success) {
                const s = this._state;
                s.pageItems     = data.results;
                s.currentPage   = data.page;
                s.totalPages    = data.total_pages;
                s.totalCount    = data.total_count;
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

    // ─── Paginate + Render ───────────────────────────────
    _paginateAndRender() {
        const cfg   = this._configs[this._activeId];
        const s     = this._state;
        const size  = cfg.pageSize || 15;
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
        s.currentPage   = page;
        s.selectedIndex = 0;
        if (s.isLocalMode) this._paginateAndRender();
        else               this._serverFetch(page, s.query);
    },

    _getPageItems() { return this._state ? this._state.pageItems : []; },

    _confirmSelection() {
        const s     = this._state;
        const items = this._getPageItems();
        if (s.selectedIndex >= 0 && s.selectedIndex < items.length) {
            this._selectItem(items[s.selectedIndex]);
        }
    },

    _selectItem(item) {
        const cfg = this._configs[this._activeId];
        if (cfg.onSelect && typeof cfg.onSelect === 'function') cfg.onSelect(item);
        this.close();
    },

    // ═══════════════════════════════════════════════════
    //  RENDERING
    // ═══════════════════════════════════════════════════

    _renderTable(items, cfg) {
        const container = document.getElementById('gsm-results');
        if (!items || items.length === 0) { this._showEmpty('No results found'); return; }

        const cols   = cfg.displayColumns || [];
        const query  = (this._state.query || '').toLowerCase();
        const tokens = query
            ? query.replace(/[^a-z0-9]+/g, ' ').split(' ').filter(Boolean)
            : [];

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
                if (tokens.length > 0) display = this._highlightTokens(display, tokens);
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
            result = result.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
        });
        return result;
    },

    _renderPagination() {
        const s         = this._state;
        const container = document.getElementById('gsm-pagination');
        if (s.totalPages <= 1) { container.innerHTML = ''; return; }

        const pages = this._getPaginationRange(s.currentPage, s.totalPages);
        let html = `<button ${s.currentPage === 1 ? 'disabled' : ''} onclick="GlobalSearchModal.goToPage(${s.currentPage - 1})">«</button>`;

        pages.forEach(p => {
            if (p === '...') {
                html += `<button disabled>…</button>`;
            } else {
                const active = p === s.currentPage ? ' active' : '';
                html += `<button class="${active}" onclick="GlobalSearchModal.goToPage(${p})">${p}</button>`;
            }
        });

        html += `<button ${s.currentPage === s.totalPages ? 'disabled' : ''} onclick="GlobalSearchModal.goToPage(${s.currentPage + 1})">»</button>`;
        container.innerHTML = html;
    },

    _getPaginationRange(current, total) {
        if (total <= 9) return Array.from({ length: total }, (_, i) => i + 1);
        const pages = new Set();
        for (let i = 1; i <= Math.min(4, total); i++) pages.add(i);
        for (let i = Math.max(1, current - 1); i <= Math.min(total, current + 1); i++) pages.add(i);
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

    _renderFooterInfo() {
        const s  = this._state;
        const el = document.getElementById('gsm-result-count');
        if (el) {
            const cfg   = this._configs[this._activeId];
            const size  = cfg.pageSize || 15;
            const start = (s.currentPage - 1) * size + 1;
            const end   = Math.min(s.currentPage * size, s.totalCount);
            el.textContent = `${start}–${end} of ${s.totalCount}`;
        }
    },

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

    _onRowClick(idx) {
        this._state.selectedIndex = idx;
        this._updateSelection();
    },

    _onRowDblClick(idx) {
        this._state.selectedIndex = idx;
        this._confirmSelection();
    },

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

    openById(modalId) { this.open(modalId); }
};

window.GlobalSearchModal = GlobalSearchModal;

/* ── Reusable pure-function utilities ──
   Exported for InlineSearchWidget and other consumers.
   No modal DOM dependency. */

/** Simple O(n) search — used as bare fallback when engine unavailable. */
function _bareSearch(query, items, cfg) {
    if (!query) return [...items];
    const tokens = query.toLowerCase().replace(/[^a-z0-9]+/g, ' ').split(' ').filter(Boolean);
    return items.filter(item =>
        tokens.every(token =>
            (cfg.searchFields || []).some(field => {
                const val = item[field];
                return val !== null && val !== undefined &&
                       String(val).toLowerCase().includes(token);
            })
        )
    );
}

export function fuzzySearch(items, query, searchFields, primaryKey) {
    if (!query) return [...items];
    const tokens = query.toLowerCase().replace(/[^a-z0-9]+/g, ' ').split(' ').filter(Boolean);
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
        result = result.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
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
