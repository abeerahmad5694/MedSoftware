/**
 * Designer workbench.
 *
 * No rendering logic lives here. Every preview refresh is one POST to
 * /api/render/ — the exact same endpoint document_printer.js uses for
 * real printing. This file only ever edits the `configuration` object
 * (ordered lists of field/column/totals entries per section) and asks
 * the server to turn it into HTML.
 *
 * NEW FEATURES (this version):
 * - Logo: file-upload input (no URL textbox). Uploaded via /api/upload-image/.
 *   Falls back to company logo_url from document_data if no override saved.
 * - Logo width/height: pixel inputs shown for image fields.
 * - Prefix / Suffix: text inputs for any field (e.g. prefix "INV-" on invoice_number).
 * - format_string: for item columns, a Python-style template like
 *   "{product_name} ({discount_percent}%)" that merges multiple fields.
 * - hide_if_zero / always_show: toggles to control zero-value visibility.
 * - Live preview uses real company data from configuration OR sample data.
 */
(function () {
    "use strict";

    // ── state ────────────────────────────────────────────────────────────
    const state = {
        configuration: window.INITIAL_CONFIGURATION,
        documentType: window.DESIGNER_DOCUMENT_TYPE,
        pageType: window.DESIGNER_PAGE_TYPE,
        registry: null,
        activeSection: "header",
        selected: null,            // {section, key}
        searchTerm: "",
        dragFromIndex: null,
        renderTimer: null,
        companyData: null,         // Fetched once from the server
    };

    const SECTION_LABELS = { header: "Header", customer: "Customer", items: "Items", totals: "Totals", footer: "Footer", barcode: "Barcode" };
    const EDITABLE_SECTIONS = ["header", "customer", "items", "totals", "footer"];
    const UPLOAD_API = "/invoice-designer/api/upload-image/";

    // ── sample / preview data ────────────────────────────────────────────

    function buildSampleDocumentData(documentType) {
        const isPurchase = documentType === "purchase_invoice";
        const company = (state.companyData && state.companyData.company) || {
            name: "Al-Noor Traders",
            address: "Main Commercial Market, Rawalpindi",
            phone: "+92 51 1234567",
            email: "info@alnoor.example",
            license_number: "LIC-88213",
            logo_url: "",
        };
        const branch = (state.companyData && state.companyData.branch) || {
            name: "Rawalpindi Branch",
            address: "Shop 4, Commercial Market",
            phone: "+92 51 1234567",
            email: "rwp@alnoor.example",
            license_number: "LIC-88213-B",
            logo_url: "",
        };
        let items = [];
        if (documentType === "purchase_invoice") {
            items = [
                { product_name: "Basmati Rice 5kg", product_name_ur: "باسمتی چاول 5 کلو", category: "Grocery", quantity: 20, unit: "Kg", rate: "1,000.00", discount_percent: 5, discount_amount: "1,000.00", amount: "20,000.00", batch_number: "B-12", batch_quantity: 20, expiry_date: "2027-01", pack_quantity_received: 20, trade_price: "1,150.00", retail_price: "1,200.00", old_cost: "980.00", landed_cost: "1,015.00" },
                { product_name: "Cooking Oil 1L", product_name_ur: "کوکنگ آئل 1 لیٹر", category: "Grocery", quantity: 40, unit: "Ltr", rate: "180.00", discount_percent: 0, discount_amount: "0.00", amount: "7,200.00", batch_number: "B-07", batch_quantity: 40, expiry_date: "2026-11", pack_quantity_received: 40, trade_price: "195.00", retail_price: "210.00", old_cost: "170.00", landed_cost: "182.00" },
            ];
        } else if (documentType === "voucher") {
            items = [
                { account_code: "A-100", account_name: "Cash Account", counter_account_code: "C-0012", counter_account_name: "Walk-in Customer", description: "Payment received", debit_amount: "3,050.00", credit_amount: "0.00", amount: "3,050.00" },
                { account_code: "C-0012", account_name: "Walk-in Customer", counter_account_code: "A-100", counter_account_name: "Cash Account", description: "Payment received", debit_amount: "0.00", credit_amount: "3,050.00", amount: "3,050.00" },
            ];
        } else {
            items = [
                { product_name: "Basmati Rice 5kg", product_name_ur: "باسمتی چاول 5 کلو", category: "Grocery", quantity: 2, unit: "Kg", rate: "1,200.00", discount_percent: 5, discount_amount: "120.00", amount: "2,400.00", cost_price: "1,015.00", net_cost: "2,030.00", item_notes: "" },
                { product_name: "Cooking Oil 1L", product_name_ur: "کوکنگ آئل 1 لیٹر", category: "Grocery", quantity: 4, unit: "Ltr", rate: "200.00", discount_percent: 0, discount_amount: "0.00", amount: "800.00", cost_price: "182.00", net_cost: "728.00", item_notes: "" },
            ];
        }

        return {
            bill_number: documentType === "voucher" ? "CR-10245" : "10245",
            invoice_title: documentType === "voucher" ? "CASH RECEIPT VOUCHER" : "INVOICE",
            invoice_date: new Date().toLocaleDateString(),
            salesman: "Ali Raza",
            cashier: "Front Desk 1",
            terminal: "POS-01",
            remarks: "Handle with care.",
            terms_and_conditions: "Goods once sold are not returnable.",
            printed_by: "System",
            print_date: new Date().toLocaleDateString(),
            print_time: new Date().toLocaleTimeString(),
            company,
            branch,
            customer: { account_code: "C-0012", name: "Walk-in Customer", address: "Shop 5, Main Bazaar", phone: "+92 300 1234567" },
            totals: {
                total_items: 2,
                subtotal: "3,200.00",
                discount_percent: 0,
                discount_amount: "150.00",
                gst_percent: 0,
                gst_amount: "0.00",
                delivery_charges: "0.00",
                misc_charges: "0.00",
                net_total: "3,050.00",
                cash_received: "3,050.00",
                bank_received: "0.00",
                change_amount: "0.00",
                previous_balance: "1,250.00",
            },
            items: items,
        };
    }

    // Fetch company info once so the designer preview shows the real logo
    async function fetchCompanyPreviewData() {
        try {
            const res = await fetch("/invoice-designer/api/company-preview/");
            if (res.ok) state.companyData = await res.json();
        } catch (_) { /* not fatal */ }
    }

    // ── utils ────────────────────────────────────────────────────────────

    function debounceRender() {
        clearTimeout(state.renderTimer);
        state.renderTimer = setTimeout(renderPreview, 150);
    }

    function resolveStyle(styleName, overrides) {
        const base = Object.assign({}, state.registry.style_base);
        Object.assign(base, state.registry.style_presets[styleName] || {});
        if (overrides) Object.assign(base, overrides);
        return base;
    }

    function itemColumnRegistry() {
        return (state.registry.item_columns_by_document_type || {})[state.documentType] || {};
    }

    function sectionList(sectionKey) {
        const section = state.configuration.sections[sectionKey];
        if (!section) return [];
        return sectionKey === "items" ? section.columns : section.fields;
    }

    function renumberOrder(list) {
        list.forEach((entry, index) => { if ("order" in entry) entry.order = index + 1; });
    }

    // ── bootstrap ────────────────────────────────────────────────────────

    async function loadRegistry() {
        const response = await fetch(window.FIELD_REGISTRY_API_URL);
        state.registry = await response.json();
    }

    // ── left rail ────────────────────────────────────────────────────────

    function renderLeftPanel() {
        const tabsContainer = document.getElementById("section-tabs");
        tabsContainer.innerHTML = "";

        Object.keys(state.configuration.sections).forEach((sectionKey) => {
            const section = state.configuration.sections[sectionKey];
            const tab = document.createElement("div");
            tab.className = "section-item" + (state.activeSection === sectionKey ? " active" : "");
            tab.dataset.section = sectionKey;
            tab.innerHTML = `<span class="section-dot"></span><span class="section-name">${SECTION_LABELS[sectionKey] || sectionKey}</span>`;

            const toggle = document.createElement("span");
            toggle.className = "toggle" + (section.visible !== false ? " on" : "");
            toggle.title = "Show/hide this whole section";
            toggle.addEventListener("click", (event) => {
                event.stopPropagation();
                section.visible = section.visible === false ? true : false;
                toggle.classList.toggle("on", section.visible);
                debounceRender();
            });
            tab.appendChild(toggle);

            tab.addEventListener("click", () => {
                state.activeSection = sectionKey;
                state.selected = null;
                state.searchTerm = "";
                document.getElementById("field-search").value = "";
                renderLeftPanel();
                renderPropertyEmptyState();
            });

            tabsContainer.appendChild(tab);
        });

        renderFieldLibrary();
    }

    function registryEntriesForActiveSection() {
        const section = state.activeSection;
        if (section === "items") {
            return Object.entries(itemColumnRegistry()).map(([key, entry]) => ({ key, ...entry }));
        }
        if (section === "totals") {
            return Object.entries(state.registry.totals_fields).map(([key, entry]) => ({ key, ...entry }));
        }
        if (EDITABLE_SECTIONS.includes(section)) {
            const allowedCategories = state.registry.section_categories[section] || [];
            return Object.entries(state.registry.fields)
                .filter(([, entry]) => allowedCategories.includes(entry.category))
                .map(([key, entry]) => ({ key, ...entry }));
        }
        return [];
    }

    function renderFieldLibrary() {
        const libraryContainer = document.getElementById("field-library");
        const addedContainer = document.getElementById("added-fields");
        libraryContainer.innerHTML = "";
        addedContainer.innerHTML = "";

        if (!EDITABLE_SECTIONS.includes(state.activeSection)) {
            libraryContainer.innerHTML = '<div class="empty-state">This document type has its own dedicated configuration.</div>';
            return;
        }

        const list = sectionList(state.activeSection);
        const addedKeys = new Set(list.map((entry) => entry.field));
        const term = state.searchTerm.trim().toLowerCase();

        const candidates = registryEntriesForActiveSection()
            .filter((entry) => !addedKeys.has(entry.key))
            .filter((entry) => !term || entry.key.toLowerCase().includes(term) || (entry.label || "").toLowerCase().includes(term));

        const byCategory = {};
        candidates.forEach((entry) => {
            const category = entry.category || "Fields";
            (byCategory[category] = byCategory[category] || []).push(entry);
        });

        const categoryNames = Object.keys(byCategory);
        if (!categoryNames.length) {
            libraryContainer.innerHTML = '<div class="empty-state small">Everything available is already added.</div>';
        }

        categoryNames.forEach((category) => {
            const heading = document.createElement("div");
            heading.className = "library-category";
            heading.textContent = category;
            libraryContainer.appendChild(heading);

            byCategory[category].forEach((entry) => {
                const row = document.createElement("div");
                row.className = "library-row";
                row.innerHTML = `<span class="library-row-label">${entry.label}</span>`;
                const addButton = document.createElement("button");
                addButton.type = "button";
                addButton.className = "add-btn";
                addButton.textContent = "+";
                addButton.title = `Add ${entry.label}`;
                addButton.addEventListener("click", () => addFieldToActiveSection(entry.key));
                row.appendChild(addButton);
                libraryContainer.appendChild(row);
            });
        });

        // Currently added fields — drag-to-reorder
        list.forEach((entry, index) => {
            const registryEntry = lookupRegistryEntry(state.activeSection, entry.field) || {};
            const row = document.createElement("div");
            row.className = "added-row" + (isSelected(state.activeSection, entry.field) ? " active" : "");
            row.draggable = true;
            row.dataset.index = String(index);

            const handle = document.createElement("span");
            handle.className = "drag-handle";
            handle.title = "Drag to reorder";
            handle.textContent = "⠿";
            row.appendChild(handle);

            const nameSpan = document.createElement("span");
            nameSpan.className = "added-row-label";
            nameSpan.textContent = entry.label || registryEntry.label || entry.field;
            if (registryEntry.field_type === "image") nameSpan.textContent += " 🖼";
            row.appendChild(nameSpan);

            const controls = document.createElement("span");
            controls.className = "added-row-controls";

            const visibleToggle = document.createElement("span");
            visibleToggle.className = "toggle small" + (entry.visible !== false ? " on" : "");
            visibleToggle.title = "Show/hide";
            visibleToggle.addEventListener("click", (event) => {
                event.stopPropagation();
                entry.visible = entry.visible === false ? true : false;
                visibleToggle.classList.toggle("on", entry.visible);
                debounceRender();
            });
            controls.appendChild(visibleToggle);

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "icon-btn remove";
            removeButton.textContent = "×";
            removeButton.title = "Remove";
            removeButton.addEventListener("click", (event) => {
                event.stopPropagation();
                removeFieldFromActiveSection(index);
            });
            controls.appendChild(removeButton);

            row.appendChild(controls);
            row.addEventListener("click", () => selectField(state.activeSection, entry.field));
            attachDragHandlers(row, index);
            addedContainer.appendChild(row);
        });

        if (!list.length) {
            addedContainer.innerHTML = '<div class="empty-state small">No fields added yet — use the (+) buttons above.</div>';
        }
    }

    // ── drag & drop ──────────────────────────────────────────────────────

    function attachDragHandlers(row, index) {
        row.addEventListener("dragstart", (event) => {
            state.dragFromIndex = index;
            row.classList.add("dragging");
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", String(index));
        });
        row.addEventListener("dragend", () => {
            row.classList.remove("dragging");
            document.querySelectorAll(".added-row.drag-over").forEach((el) => el.classList.remove("drag-over"));
        });
        row.addEventListener("dragover", (event) => { event.preventDefault(); row.classList.add("drag-over"); });
        row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
        row.addEventListener("drop", (event) => {
            event.preventDefault();
            row.classList.remove("drag-over");
            const fromIndex = state.dragFromIndex !== null ? state.dragFromIndex : parseInt(event.dataTransfer.getData("text/plain"), 10);
            reorderActiveSectionField(fromIndex, index);
            state.dragFromIndex = null;
        });
    }

    function reorderActiveSectionField(fromIndex, toIndex) {
        const list = sectionList(state.activeSection);
        if (fromIndex === toIndex || fromIndex < 0 || fromIndex >= list.length || toIndex < 0 || toIndex >= list.length) return;
        const [moved] = list.splice(fromIndex, 1);
        list.splice(toIndex, 0, moved);
        renumberOrder(list);
        renderFieldLibrary();
        debounceRender();
    }

    function lookupRegistryEntry(section, key) {
        if (section === "items") return itemColumnRegistry()[key];
        if (section === "totals") return state.registry.totals_fields[key];
        return state.registry.fields[key];
    }

    function addFieldToActiveSection(key) {
        const section = state.activeSection;
        const list = sectionList(section);
        const registryEntry = lookupRegistryEntry(section, key) || {};

        if (section === "items") {
            list.push({ field: key, label: registryEntry.label, visible: true, order: list.length + 1, width: registryEntry.default_width || "auto", style: "normal" });
        } else if (section === "totals") {
            list.push({ field: key, visible: true, order: list.length + 1, label: registryEntry.label, style: registryEntry.default_style || "normal" });
        } else {
            list.push({ field: key, visible: true, style: registryEntry.default_style || "normal" });
        }

        renumberOrder(list);
        renderFieldLibrary();
        debounceRender();
        selectField(section, key);
    }

    function removeFieldFromActiveSection(index) {
        const list = sectionList(state.activeSection);
        const removed = list.splice(index, 1)[0];
        renumberOrder(list);
        if (state.selected && state.selected.section === state.activeSection && removed && state.selected.key === removed.field) {
            state.selected = null;
            renderPropertyEmptyState();
        }
        renderFieldLibrary();
        debounceRender();
    }

    function isSelected(section, key) {
        return !!state.selected && state.selected.section === section && state.selected.key === key;
    }

    // ── preview ──────────────────────────────────────────────────────────

    async function renderPreview() {
        const response = await fetch(window.RENDER_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ configuration: state.configuration, document_data: buildSampleDocumentData(state.documentType) }),
        });
        const data = await response.json();
        const frame = document.getElementById("page-frame");
        frame.innerHTML = data.html;
        applyPreviewScale();
        reselectIfStillPresent();
    }

    function applyPreviewScale() {
        const wrap = document.getElementById("canvas-wrap");
        const frame = document.getElementById("page-frame");
        const documentEl = frame.firstElementChild;
        if (!documentEl) return;
        const availableWidth = wrap.clientWidth - 40;
        const naturalWidth = documentEl.getBoundingClientRect().width / (frame._scale || 1);
        const scale = Math.min(1, availableWidth / naturalWidth);
        frame._scale = scale;
        frame.style.transform = `scale(${scale})`;
    }

    function reselectIfStillPresent() {
        if (!state.selected) return;
        const el = document.querySelector(`[data-field="${dataFieldFor(state.selected.section, state.selected.key)}"]`);
        if (el) el.classList.add("selected");
    }

    function dataFieldFor(section, key) {
        return section === "items" ? `items:column:${key}` : `${section}:${key}`;
    }

    // ── selection ────────────────────────────────────────────────────────

    function onPreviewClick(event) {
        // Allow clicking on td (data cells) to select the column via its th
        const tdTarget = event.target.closest("td");
        if (tdTarget) {
            // Find which column index this td corresponds to
            const tr = tdTarget.parentElement;
            const tdIndex = Array.from(tr.children).indexOf(tdTarget);
            const table = tr.closest("table");
            if (table) {
                const th = table.querySelector("thead tr")?.children[tdIndex];
                if (th && th.dataset.field) {
                    document.querySelectorAll(".doc-field.selected, th.selected, td.selected").forEach((el) => el.classList.remove("selected"));
                    th.classList.add("selected");
                    tdTarget.classList.add("selected");
                    const parts = th.dataset.field.split(":");
                    if (parts[0] === "items" && parts[1] === "column") {
                        state.activeSection = "items";
                        selectField("items", parts[2]);
                        return;
                    }
                }
            }
        }
        const target = event.target.closest("[data-field]");
        if (!target) return;
        document.querySelectorAll(".doc-field.selected, th.selected, td.selected").forEach((el) => el.classList.remove("selected"));
        target.classList.add("selected");
        const parts = target.dataset.field.split(":");
        if (parts[0] === "items" && parts[1] === "column") {
            state.activeSection = "items";
            selectField("items", parts[2]);
            return;
        }
        state.activeSection = parts[0];
        selectField(parts[0], parts[1]);
    }

    function selectField(section, key) {
        state.selected = { section, key };
        state.activeSection = section;
        renderLeftPanel();
        openFieldEditor(section, key);
    }

    // ── right rail ───────────────────────────────────────────────────────

    function renderPropertyEmptyState() {
        document.getElementById("property-panel").innerHTML =
            '<div class="empty-state">Click any field — in the preview, or in the list on the left — to edit it here.</div>';
    }

    function findFieldConfig(section, key) {
        return sectionList(section).find((entry) => entry.field === key);
    }

    function openFieldEditor(section, key) {
        const fieldConfig = findFieldConfig(section, key);
        const panel = document.getElementById("property-panel");
        if (!fieldConfig) { renderPropertyEmptyState(); return; }

        const registryEntry = lookupRegistryEntry(section, key) || {};
        const style = resolveStyle(fieldConfig.style || "normal", fieldConfig.style_overrides);
        const presetOptions = Object.keys(state.registry.style_presets)
            .map((name) => `<option value="${name}" ${fieldConfig.style === name ? "selected" : ""}>${name}</option>`)
            .join("");

        let contentField = "";

        // ── IMAGE FIELD (logo) ─────────────────────────────────────────
        if (registryEntry.field_type === "image") {
            const currentUrl = fieldConfig.custom_value || "";
            contentField = `
                <div class="prop-group">
                    <label>Custom Logo <span class="hint">(leave blank to use real ${key === "branch_logo" ? "branch" : "company"} logo)</span></label>
                    ${currentUrl ? `<div style="margin-bottom:6px"><img src="${currentUrl}" alt="logo" style="max-height:60px;max-width:100%;border:1px solid #444;border-radius:4px;padding:2px;"></div>` : ""}
                    <input type="file" id="prop-logo-file" accept="image/*" style="margin-bottom:6px;">
                    ${currentUrl ? `<button type="button" id="prop-logo-clear" class="icon-btn" style="margin-bottom:6px;font-size:11px;">✕ Clear custom logo</button>` : ""}
                </div>
                <div class="prop-row">
                    <div class="prop-group"><label>Width (e.g. 60px, 30mm)</label><input type="text" id="prop-logo-width" value="${fieldConfig.logo_width || ""}"></div>
                    <div class="prop-group"><label>Height (e.g. 40px, 20mm)</label><input type="text" id="prop-logo-height" value="${fieldConfig.logo_height || ""}"></div>
                </div>`;

            // ── ITEMS COLUMN ───────────────────────────────────────────────
        } else if (section === "items") {
            contentField = `
                <div class="prop-group"><label>Column heading</label><input type="text" id="prop-label" value="${fieldConfig.label || ""}"></div>
                <div class="prop-row">
                    <div class="prop-group"><label>Width</label><input type="text" id="prop-width" value="${fieldConfig.width || ""}"></div>
                </div>
                <div class="prop-group">
                    <label>Format string <span class="hint">(merge fields, e.g. <code>{product_name} ({discount_percent}%)</code>)</span></label>
                    <input type="text" id="prop-format-string" placeholder="e.g. {product_name} ({discount_percent}%)" value="${fieldConfig.format_string || ""}">
                </div>
                <div class="prop-toggle-row">
                    <span>Always show column (even if all values are 0)</span>
                    <span class="toggle small ${fieldConfig.always_show ? "on" : ""}" id="prop-always-show"></span>
                </div>
                <div class="prop-toggle-row">
                    <span>Show table borders</span>
                    <span class="toggle small ${state.configuration.sections.items.table_borders ? "on" : ""}" id="prop-table-borders"></span>
                </div>`;

            // ── TOTALS FIELD ───────────────────────────────────────────────
        } else if (section === "totals") {
            contentField = `
                <div class="prop-group"><label>Label</label><input type="text" id="prop-label" value="${fieldConfig.label || ""}"></div>
                <div class="prop-toggle-row">
                    <span>Hide when value is zero</span>
                    <span class="toggle small ${fieldConfig.hide_if_zero !== false ? "on" : ""}" id="prop-hide-if-zero"></span>
                </div>`;

            // ── REGULAR TEXT/STATIC FIELD ──────────────────────────────────
        } else {
            const prefix = fieldConfig.prefix || "";
            const suffix = fieldConfig.suffix || "";
            if (registryEntry.data_source) {
                contentField = `
                    <div class="prop-group">
                        <label>Custom text <span class="hint">(leave blank to use real database value)</span></label>
                        <input type="text" id="prop-custom-value" placeholder="Type to override…" value="${fieldConfig.custom_value || ""}">
                    </div>`;
            } else if (registryEntry.field_type !== "static_text") {
                contentField = `
                    <div class="prop-group">
                        <label>Text <span class="hint">(no database source — type manually)</span></label>
                        <input type="text" id="prop-custom-value" placeholder="Type here…" value="${fieldConfig.custom_value || ""}">
                    </div>`;
            }
            contentField += `
                <div class="prop-row">
                    <div class="prop-group"><label>Prefix <span class="hint">(e.g. INV-)</span></label><input type="text" id="prop-prefix" value="${prefix}"></div>
                    <div class="prop-group"><label>Suffix</label><input type="text" id="prop-suffix" value="${suffix}"></div>
                </div>`;
            if (section === "customer") {
                contentField += `
                    <div class="prop-group">
                        <label>Exclude Accounts <span class="hint">(comma separated names or codes)</span></label>
                        <input type="text" id="prop-exclude-accounts" placeholder="e.g. Walk-in, C-001" value="${state.configuration.sections.customer.exclude_accounts || ""}">
                    </div>`;
            }
        }

        panel.innerHTML = `
            <div class="field-key">${section} · ${registryEntry.label || key}</div>
            ${contentField}
            <div class="prop-toggle-row">
                <span>Visible</span>
                <span class="toggle ${fieldConfig.visible !== false ? "on" : ""}" id="prop-visible"></span>
            </div>
            <div class="prop-group">
                <label>Style preset</label>
                <select id="prop-style-preset">${presetOptions}</select>
            </div>
            <div class="prop-row">
                <div class="prop-group"><label>Font size</label><input type="number" id="prop-font-size" value="${style.font_size}"></div>
                <div class="prop-group">
                    <label>Alignment</label>
                    <select id="prop-alignment">
                        ${["left", "center", "right"].map((a) => `<option value="${a}" ${style.alignment === a ? "selected" : ""}>${a}</option>`).join("")}
                    </select>
                </div>
            </div>
            <div class="prop-toggle-row"><span>Bold</span><span class="toggle ${style.bold ? "on" : ""}" id="prop-bold"></span></div>
            <div class="prop-toggle-row"><span>Italic</span><span class="toggle ${style.italic ? "on" : ""}" id="prop-italic"></span></div>
            <div class="prop-toggle-row"><span>Underline</span><span class="toggle ${style.underline ? "on" : ""}" id="prop-underline"></span></div>
            <div class="prop-group"><label>Text color</label><input type="color" id="prop-text-color" value="${toHex(style.text_color)}"></div>
        `;

        function ensureOverrides() {
            if (!fieldConfig.style_overrides) fieldConfig.style_overrides = {};
            return fieldConfig.style_overrides;
        }

        // ── bind common toggles / inputs ────────────────────────────────
        bindToggle("prop-visible", (value) => (fieldConfig.visible = value));
        bindToggle("prop-bold", (value) => (ensureOverrides().bold = value));
        bindToggle("prop-italic", (value) => (ensureOverrides().italic = value));
        bindToggle("prop-underline", (value) => (ensureOverrides().underline = value));

        bindInput("prop-style-preset", (value) => { fieldConfig.style = value; fieldConfig.style_overrides = {}; openFieldEditor(section, key); });
        bindInput("prop-font-size", (value) => (ensureOverrides().font_size = parseInt(value, 10) || 12));
        bindInput("prop-alignment", (value) => (ensureOverrides().alignment = value));
        bindInput("prop-text-color", (value) => (ensureOverrides().text_color = value));
        bindInput("prop-custom-value", (value) => (fieldConfig.custom_value = value));
        bindInput("prop-label", (value) => { fieldConfig.label = value; renderFieldLibrary(); });
        bindInput("prop-width", (value) => (fieldConfig.width = value));
        bindInput("prop-prefix", (value) => (fieldConfig.prefix = value));
        bindInput("prop-suffix", (value) => (fieldConfig.suffix = value));
        bindInput("prop-format-string", (value) => (fieldConfig.format_string = value));
        bindInput("prop-logo-width", (value) => (fieldConfig.logo_width = value));
        bindInput("prop-logo-height", (value) => (fieldConfig.logo_height = value));
        bindToggle("prop-always-show", (value) => (fieldConfig.always_show = value));
        bindToggle("prop-hide-if-zero", (value) => (fieldConfig.hide_if_zero = value));
        bindToggle("prop-table-borders", (value) => (state.configuration.sections.items.table_borders = value));
        bindInput("prop-exclude-accounts", (value) => (state.configuration.sections.customer.exclude_accounts = value));

        // Logo clear button
        const clearBtn = document.getElementById("prop-logo-clear");
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                fieldConfig.custom_value = "";
                openFieldEditor(section, key);
                debounceRender();
            });
        }

        // Logo file upload
        const fileInput = document.getElementById("prop-logo-file");
        if (fileInput) {
            fileInput.addEventListener("change", async () => {
                const file = fileInput.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append("image", file);
                try {
                    const res = await fetch(UPLOAD_API, { method: "POST", body: formData });
                    if (!res.ok) throw new Error("Upload failed");
                    const data = await res.json();
                    fieldConfig.custom_value = data.url;
                    openFieldEditor(section, key); // re-render panel to show preview
                    debounceRender();
                } catch (err) {
                    alert("Logo upload failed: " + err.message);
                }
            });
        }
    }

    function bindInput(id, apply) {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("input", () => { apply(el.value); debounceRender(); });
        el.addEventListener("change", () => { apply(el.value); debounceRender(); });
    }

    function bindToggle(id, apply) {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("click", () => {
            const next = !el.classList.contains("on");
            el.classList.toggle("on", next);
            apply(next);
            debounceRender();
        });
    }

    function toHex(color) {
        if (!color || color === "transparent") return "#ffffff";
        return color.startsWith("#") ? color : "#ffffff";
    }

    // ── save ─────────────────────────────────────────────────────────────

    async function saveConfiguration() {
        const response = await fetch(window.CONFIGURATION_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ document_type: state.documentType, page_type: state.pageType, configuration: state.configuration }),
        });
        if (response.ok) {
            const cacheKey = `${state.documentType}_${state.pageType}`;
            if (window.IndexDBConfig && typeof window.IndexDBConfig.save_update_record === "function") {
                window.IndexDBConfig.save_update_record("template_configs", {
                    key: cacheKey,
                    document_type: state.documentType,
                    page_type: state.pageType,
                    configuration: state.configuration,
                    updated_at: new Date().toISOString(),
                }).catch(e => console.warn("Could not save to local IndexedDB:", e));
            }
        }
        const button = document.getElementById("save-button");
        const original = button.textContent;
        button.textContent = response.ok ? "✓ Saved" : "Save failed";
        button.classList.toggle("save-error", !response.ok);
        setTimeout(() => { button.textContent = original; button.classList.remove("save-error"); }, 1400);
    }

    function openPrintPreview() {
        if (window.DocumentPrinter) {
            window.DocumentPrinter.openPreviewModal({
                documentType: state.documentType,
                pageType: state.pageType,
                dataSource: "local",
                payload: buildSampleDocumentData(state.documentType),
            });
        }
    }

    // ── init ─────────────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", async () => {
        await Promise.all([loadRegistry(), fetchCompanyPreviewData()]);
        renderLeftPanel();
        renderPropertyEmptyState();
        renderPreview();

        document.getElementById("page-frame").addEventListener("click", onPreviewClick);
        document.getElementById("save-button").addEventListener("click", saveConfiguration);
        const previewButton = document.getElementById("preview-button");
        if (previewButton) previewButton.addEventListener("click", openPrintPreview);

        const searchInput = document.getElementById("field-search");
        searchInput.addEventListener("input", () => {
            state.searchTerm = searchInput.value;
            renderFieldLibrary();
        });

        window.addEventListener("resize", applyPreviewScale);
    });
})();
