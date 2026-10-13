/**
 * DocumentPrinter
 * -----------------
 * The one public API every other app in the ERP calls to print or
 * preview anything. It never contains rendering logic — it only
 * decides *where document_data comes from*, then hands both the
 * configuration and the data to the exact same /api/render/ endpoint
 * the designer's live preview uses.
 *
 * Preview = Print output (requirement #6): both printDocument() and
 * openPreviewModal() render into the SAME modal, with the SAME CSS,
 * at real page size. Printing (requirement #7) only ever prints that
 * modal's page — the host page's own UI is never part of the output,
 * because print.css hides everything outside #print-modal-page.
 *
 * Usage (exact shape requested):
 *
 *   DocumentPrinter.printDocument({
 *       bill_no: 10245,
 *       model_name: "Invoice",
 *       page_type: "thermal_80",
 *       document_type: "pos_invoice",
 *       data_source: "local",           // "local" | "server"
 *       payload: {...},                 // required when data_source === "local"
 *       allow_multiple_print: false,
 *       copies: 1,
 *   });
 */


let offline_bill_no = 10000
window.DocumentPrinter = (function () {
    "use strict";

    const ENDPOINTS = {
        configuration: "/invoice-designer/api/configuration/",
        render: "/invoice-designer/api/render/",
        documentData: "/invoice-designer/api/document-data/",
    };

    let modalState = null;   // { documentType, dataSource, payload, billNumber, modelName }

    function mapLocalPayloadToDocumentData(payload) {
        if (!payload) return {};

        // Map item fields from POS payload shape -> document_data shape
        const items = (payload.items || []).map(i => ({
            product_name:     i.prod_name || i.product_name || "",
            product_name_ur:  i.prod_name_ur || i.product_name_ur || "",
            category:         i.category || "",
            quantity:         i.qty !== undefined ? i.qty : (i.quantity !== undefined ? i.quantity : ""),
            unit:             i.uom || i.unit || "",
            packing_mode:     i.packing_mode || "",
            pack_quantity:    i.pack_qty !== undefined ? i.pack_qty : (i.pack_quantity !== undefined ? i.pack_quantity : ""),
            rate:             i.rate !== undefined ? i.rate : "",
            discount_percent: i.row_discount_percent !== undefined ? i.row_discount_percent : (i.discount_percent !== undefined ? i.discount_percent : 0),
            discount_amount:  i.row_discount_amount !== undefined ? i.row_discount_amount : (i.discount_amount !== undefined ? i.discount_amount : 0),
            amount:           i.row_net_total !== undefined ? i.row_net_total : (i.amount !== undefined ? i.amount : ""),
            item_notes:       i.row_notes || i.item_notes || "",
            cost_price:       i.row_rate_cost || i.cost_price || 0,
            net_cost:         i.row_net_cost || i.net_cost || 0,
        }));

        offline_bill_no += 1;
        return {
            bill_number:  payload.bill_no || offline_bill_no,
            invoice_title: payload.invoice_title || "INVOICE",
            invoice_date: payload.invoice_date || new Date().toISOString().split('T')[0],
            salesman:     payload.salesman || "",
            cashier:      payload.cashier || "",
            terminal:     payload.terminal || "",
            remarks:      payload.header_remarks || payload.remarks || "",
            printed_by:   payload.cashier || payload.printed_by || "",
            print_date:   new Date().toISOString().split('T')[0],
            print_time:   new Date().toTimeString().split(' ')[0],

            company: payload.company || {
                name: "", address: "", phone: "", email: "", license_number: "", logo_url: ""
            },
            branch: payload.branch || {
                name: "", address: "", phone: "", email: "", license_number: "", logo_url: ""
            },
            customer: {
                name:         payload.customer_name || "",
                address:      payload.customer_address || "",
                phone:        payload.customer_phone || "",
                account_code: payload.header_acc_code || "",
            },
            totals: {
                total_items:      payload.header_total_items !== undefined ? payload.header_total_items : "",
                subtotal:         payload.header_item_total !== undefined ? payload.header_item_total : 0,
                discount_percent: payload.header_discount_percent || 0,
                discount_amount:  payload.header_discount_amount || 0,
                delivery_charges: payload.header_delivery_charges || 0,
                gst_percent:      payload.header_gst_percent || 0,
                gst_amount:       payload.header_gst_amount || 0,
                misc_charges:     payload.header_misc_charges || payload.header_msc_charges || 0,
                net_total:        payload.header_net_total !== undefined ? payload.header_net_total : 0,
                cash_received:    payload.header_cash_paid || 0,
                bank_received:    payload.header_bank_paid || 0,
                change_amount:    payload.header_change_amount || 0,
            },
            items,
        };
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, options);
        if (!response.ok) {
            const body = await response.text();
            throw new Error(`DocumentPrinter: request to ${url} failed (${response.status}): ${body}`);
        }
        return response.json();
    }

    async function getLocalTemplateConfig(documentType, pageType) {
        const cacheKey = `${documentType}_${pageType}`;
        if (window.IndexDBConfig && typeof window.IndexDBConfig.get_record === "function") {
            try {
                const rec = await window.IndexDBConfig.get_record("template_configs", cacheKey);
                if (rec && rec.configuration) {
                    return rec;
                }
            } catch (e) {
                console.warn("Error reading template config from IndexedDB:", e);
            }
        }
        return null;
    }

    async function saveLocalTemplateConfig(documentType, pageType, configuration, updatedAt) {
        const cacheKey = `${documentType}_${pageType}`;
        const record = {
            key: cacheKey,
            document_type: documentType,
            page_type: pageType,
            configuration: configuration,
            updated_at: updatedAt || new Date().toISOString(),
        };
        if (window.IndexDBConfig && typeof window.IndexDBConfig.save_update_record === "function") {
            try {
                await window.IndexDBConfig.save_update_record("template_configs", record);
            } catch (e) {
                console.warn("Error saving template config to IndexedDB:", e);
            }
        }
    }

    async function loadConfiguration(documentType, pageType) {
        // Try IndexedDB first
        const cached = await getLocalTemplateConfig(documentType, pageType);
        if (cached && cached.configuration) {
            return cached.configuration;
        }

        // Otherwise fetch from server and cache locally
        const query = new URLSearchParams({ document_type: documentType, page_type: pageType });
        const data = await fetchJson(`${ENDPOINTS.configuration}?${query.toString()}`);
        if (data.configuration) {
            await saveLocalTemplateConfig(documentType, pageType, data.configuration, data.updated_at);
        }
        return data.configuration;
    }

    async function loadServerDocumentData(documentType, modelName, billNumber, pageType) {
        const query = new URLSearchParams({
            document_type: documentType,
            model_name: modelName || "",
            bill_number: billNumber,
            page_type: pageType || "",
        });
        const data = await fetchJson(`${ENDPOINTS.documentData}?${query.toString()}`);

        // Sync template config cache if server provided updated info
        if (data.template_config && pageType) {
            const cached = await getLocalTemplateConfig(documentType, pageType);
            const serverUpdated = data.template_updated_at;
            if (!cached || !cached.updated_at || (serverUpdated && serverUpdated > cached.updated_at)) {
                await saveLocalTemplateConfig(documentType, pageType, data.template_config, serverUpdated);
            }
        }

        return {
            document_data: data.document_data,
            template_config: data.template_config,
            template_updated_at: data.template_updated_at,
        };
    }

    async function renderHtml(configuration, documentData) {
        const data = await fetchJson(ENDPOINTS.render, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ configuration, document_data: documentData }),
        });
        return data.html;
    }

    // ------------------------------------------------------ modal plumbing

    function ensureStylesheet() {
        if (document.querySelector("link[data-document-printer-css]")) return;
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = "/static/invoice_designer/css/designer.css";
        link.dataset.documentPrinterCss = "true";
        document.head.appendChild(link);
    }

    function ensureModal() {
        ensureStylesheet();
        let overlay = document.getElementById("print-modal-overlay");
        if (overlay) return overlay;

        const holder = document.createElement("div");
        holder.innerHTML = `
            <div class="print-modal-overlay" id="print-modal-overlay">
                <div class="print-modal">
                    <div class="print-modal-toolbar no-print">
                        <select id="print-modal-page-type">
                            <option value="thermal_58">Thermal 58mm</option>
                            <option value="thermal_80">Thermal 80mm</option>
                            <option value="a5">A5</option>
                            <option value="a4">A4</option>
                            <option value="urdu_58mm">Thermal 58mm — Urdu</option>
                            <option value="urdu_80mm">Thermal 80mm — Urdu</option>
                            <option value="urdu_a5">A5 — Urdu</option>
                            <option value="urdu_a4">A4 — Urdu</option>
                            <option value="bilingual_80mm">Thermal 80mm — Bilingual</option>
                            <option value="bilingual_a4">A4 — Bilingual</option>
                        </select>
                        <div class="spacer"></div>
                        <button id="print-modal-print-button">Print</button>
                        <button class="ghost" id="print-modal-close-button">Close</button>
                    </div>
                    <div class="print-modal-page-wrap">
                        <div class="print-modal-page" id="print-modal-page"></div>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(holder.firstElementChild);

        overlay = document.getElementById("print-modal-overlay");
        document.getElementById("print-modal-close-button").addEventListener("click", closePreviewModal);
        document.getElementById("print-modal-print-button").addEventListener("click", () => window.print());
        return overlay;
    }

    async function renderIntoModal(pageType) {
        const overlay = ensureModal();
        const pageContainer = document.getElementById("print-modal-page");

        let configuration = null;
        let documentData = null;

        if (modalState.dataSource === "local") {
            configuration = await loadConfiguration(modalState.documentType, pageType);
            documentData = (modalState.payload && modalState.payload.totals)
                ? modalState.payload
                : mapLocalPayloadToDocumentData(modalState.payload);
        } else {
            // Check if local template config already exists
            const cachedConfig = await getLocalTemplateConfig(modalState.documentType, pageType);
            const serverResult = await loadServerDocumentData(modalState.documentType, modalState.modelName, modalState.billNumber, pageType);
            documentData = serverResult.document_data;
            configuration = (cachedConfig && cachedConfig.configuration) || serverResult.template_config || await loadConfiguration(modalState.documentType, pageType);
        }

        const html = await renderHtml(configuration, documentData);
        pageContainer.innerHTML = html;
        pageContainer.dataset.pageType = pageType;
        if (!modalState.directprint) {
            overlay.classList.add("open");
        } else {
            overlay.classList.remove("open");
        }
        return html;
    }

    /**
     * Opens the professional, centered, real-size preview modal.
     * Same renderer + same CSS as printing — this IS the print output,
     * just on screen instead of on paper.
     */

    window.addEventListener('keydown',(e)=>{
        // console.log('e.key=',e.key)
        if(e.key == 'Escape'){
            e.preventDefault();
            closePreviewModal();
        }

    })
    async function openPreviewModal(options) {
        const { documentType, pageType, dataSource = "server", payload = null, billNumber, modelName, directprint = false } = options;
        if (!documentType || !pageType) {
            throw new Error("DocumentPrinter.openPreviewModal: documentType and pageType are required");
        }
        modalState = { documentType, dataSource, payload, billNumber, modelName, directprint };

        ensureModal();
        const pageTypeSelect = document.getElementById("print-modal-page-type");
        pageTypeSelect.value = pageType;
        pageTypeSelect.onchange = () => renderIntoModal(pageTypeSelect.value);

        return renderIntoModal(pageType);
    }

    function closePreviewModal() {
        const overlay = document.getElementById("print-modal-overlay");
        if (overlay) overlay.classList.remove("open");
    }

    /**
     * THE print function. Resolves document_data according to
     * data_source, opens the preview modal (never skipping it — the
     * preview IS what gets printed), then calls window.print(), which
     * (via the @media print rules in designer.css) only prints
     * #print-modal-page — never the designer/background/controls.
     */
    async function printDocument(options) {
        const {
            bill_no: billNo,
            model_name: modelName,
            page_type: pageType,
            document_type: documentType,
            data_source: dataSource = "server",
            payload = null,
            allow_multiple_print: allowMultiplePrint = false,
            copies = 1,
            directprint = false,
        } = options;

        

        if (!documentType || !pageType) {
            throw new Error("DocumentPrinter.printDocument: document_type and page_type are required");
        }
        if (dataSource === "local" && !payload) {
            throw new Error('DocumentPrinter.printDocument: payload is required when data_source is "local"');
        }

        const html = await openPreviewModal({
            documentType, pageType, dataSource, payload, billNumber: billNo, modelName, directprint,
        });

        const resolvedCopies = allowMultiplePrint ? Math.max(1, parseInt(copies, 10) || 1) : 1;
        const pageContainer = document.getElementById("print-modal-page");
        if (resolvedCopies > 1) {
            pageContainer.innerHTML = Array.from(
                { length: resolvedCopies },
                () => `<div class="print-copy">${html}</div>`
            ).join("");
        }

        if (directprint) {
            window.print();
        }
        return html;
    }

    

    return { printDocument, openPreviewModal, closePreviewModal };
})();
