/**
 * DocumentPrinter — one print API for every document.
 *
 * data_source chooses the DOCUMENT DATA:
 *   "local"  -> use payload; no document-data request. This is the default
 *               when payload is supplied and data_source is omitted.
 *   "server" -> fetch an existing database document by bill_no.
 *
 * rendering_source (renderSource is kept as a backwards-compatible alias)
 * chooses the RENDERER:
 *   "local"  -> saved IndexedDB template + OfflineTemplateEngine. It never
 *               calls configuration, registry, CSS, company, or render APIs.
 *   "server" -> POST configuration + document data to /api/render/.
 *
 * For a 100% offline print use data_source:"local", rendering_source:"local",
 * and save the template once from the online designer.
 *
 * DocumentPrinter.printDocument({
 *   bill_no: 10245,
 *   model_name: "Invoice",
 *   page_type: "thermal_80",
 *   document_type: "pos_invoice",
 *   data_source: "local",
 *   rendering_source: "local",
 *   payload: {...},
 *   allow_multiple_print: false,
 *   copies: 1,
 *   directprint: false,
 * });
 */
window.DocumentPrinter = (function () {
    "use strict";

    const ENDPOINTS = {
        configuration: "/invoice-designer/api/configuration/",
        render: "/invoice-designer/api/render/",
        documentData: "/invoice-designer/api/document-data/",
    };
    const PAGE_TYPES = [
        ["thermal_58", "Thermal 58mm"],
        ["thermal_80", "Thermal 80mm"],
        ["a5", "A5"],
        ["a4", "A4"],
        ["urdu_58mm", "Thermal 58mm — Urdu"],
        ["urdu_80mm", "Thermal 80mm — Urdu"],
        ["urdu_a5", "A5 — Urdu"],
        ["urdu_a4", "A4 — Urdu"],
        ["bilingual_80mm", "Thermal 80mm — Bilingual"],
        ["bilingual_a4", "A4 — Bilingual"],
    ];
    const VOUCHER_TITLES = {
        CR: "CASH RECEIPT VOUCHER",
        CP: "CASH PAYMENT VOUCHER",
        BR: "BANK RECEIPT VOUCHER",
        BP: "BANK PAYMENT VOUCHER",
        JV: "JOURNAL VOUCHER",
    };

    let offlineBillNumber = 10000;
    let modalState = null;

    function firstValue(object, keys, fallback = "") {
        for (const key of keys) {
            if (object && object[key] !== undefined && object[key] !== null) return object[key];
        }
        return fallback;
    }

    function numberValue(value) {
        const number = parseFloat(String(value ?? 0).replace(/,/g, ""));
        return Number.isFinite(number) ? number : 0;
    }

    function normalizeOptions(options = {}) {
        // Supplying a payload is enough for local data; an explicit
        // data_source always wins for backwards compatibility.
        const dataSource = options.dataSource ?? options.data_source ?? (options.payload ? "local" : "server");
        return {
            documentType: options.documentType ?? options.document_type,
            pageType: options.pageType ?? options.page_type,
            dataSource,
            // Local payload printing is offline by default. Existing
            // bill_no/server-data callers keep working online by default;
            // rendering_source:"local" explicitly opts into cached rendering.
            renderSource: options.rendering_source ?? options.renderSource ?? options.renderingSource ?? dataSource,
            payload: options.payload ?? null,
            billNumber: options.billNumber ?? options.bill_no,
            modelName: options.modelName ?? options.model_name ?? "",
            directprint: options.directprint ?? false,
            allowMultiplePrint: options.allowMultiplePrint ?? options.allow_multiple_print ?? false,
            copies: options.copies ?? 1,
            // Optional in-memory assets are used by the designer's full
            // preview so it can show unsaved changes. Normal printing only
            // needs document_type + page_type and the saved local bundle.
            configuration: options.configuration || null,
            registry: options.registry || null,
            companyData: options.companyData || null,
            cssText: options.cssText || "",
        };
    }

    function validateOptions(options) {
        if (!options.documentType || !options.pageType) {
            throw new Error("DocumentPrinter: document_type and page_type are required");
        }
        if (!["local", "server"].includes(options.dataSource)) {
            throw new Error('DocumentPrinter: data_source must be "local" or "server"');
        }
        if (!["local", "server"].includes(options.renderSource)) {
            throw new Error('DocumentPrinter: rendering_source must be "local" or "server"');
        }
        if (options.dataSource === "local" && !options.payload) {
            throw new Error('DocumentPrinter: payload is required when data_source is "local"');
        }
    }

    function commonDocumentData(payload, documentType, billNumber) {
        let resolvedBillNumber = firstValue(payload, ["bill_number", "bill_no", "voucher_number", "vno", "VNO"], billNumber);
        if (resolvedBillNumber === "" || resolvedBillNumber === null || resolvedBillNumber === undefined) {
            resolvedBillNumber = ++offlineBillNumber;
        }
        const now = new Date();
        const defaultTitle = documentType === "purchase_invoice" ? "PURCHASE INVOICE"
            : documentType === "quotation" ? "QUOTATION" : "INVOICE";
        const customer = payload.customer && typeof payload.customer === "object" ? payload.customer : {};
        return {
            ...payload,
            bill_number: resolvedBillNumber,
            invoice_title: firstValue(payload, ["invoice_title"], defaultTitle),
            invoice_date: firstValue(payload, ["invoice_date", "date", "DATE"], now.toISOString().split("T")[0]),
            salesman: firstValue(payload, ["salesman"], ""),
            cashier: firstValue(payload, ["cashier", "USER"], ""),
            terminal: firstValue(payload, ["terminal"], ""),
            remarks: firstValue(payload, ["remarks", "header_remarks", "REMARKS"], ""),
            printed_by: firstValue(payload, ["printed_by", "cashier", "USER"], ""),
            print_date: now.toISOString().split("T")[0],
            print_time: now.toTimeString().split(" ")[0],
            company: payload.company || { name: "", address: "", phone: "", email: "", license_number: "", logo_url: "" },
            branch: payload.branch || { name: "", address: "", phone: "", email: "", license_number: "", logo_url: "" },
            customer: {
                ...customer,
                name: firstValue(customer, ["name"], firstValue(payload, ["customer_name"], "")),
                address: firstValue(customer, ["address"], firstValue(payload, ["customer_address"], "")),
                phone: firstValue(customer, ["phone"], firstValue(payload, ["customer_phone"], "")),
                account_code: firstValue(customer, ["account_code"], firstValue(payload, ["header_acc_code", "customer_account"], "")),
            },
        };
    }

    function mapVoucherPayload(payload, billNumber) {
        const data = commonDocumentData(payload, "voucher", billNumber);
        const sourceRows = payload.items || payload.rows || payload.gledg_rows || payload.listOfVoucherLines || [];
        const billText = String(data.bill_number || "");
        const inferredType = billText.includes("-") ? billText.split("-")[0] : "";
        const voucherType = String(firstValue(payload, ["voucher_type", "voucherType", "V_TYPE"], inferredType)).trim().toUpperCase();
        if (voucherType && !String(data.bill_number).includes("-")) {
            data.bill_number = `${voucherType}-${data.bill_number}`;
        }
        data.invoice_title = firstValue(payload, ["invoice_title"], VOUCHER_TITLES[voucherType] || `VOUCHER ${voucherType}`.trim());

        const items = sourceRows.map(row => {
            const amount = firstValue(row, ["amount", "AMOUNT"], 0);
            const amountType = String(firstValue(row, ["amt_type", "amtType", "AMT_TYPE"], "")).trim().toUpperCase();
            const defaultAmountType = ["CP", "BP"].includes(voucherType) ? "DR" : "CR";
            const effectiveType = amountType || defaultAmountType;
            const debit = firstValue(row, ["debit_amount", "debit", "DEBIT_AMOUNT"], null);
            const credit = firstValue(row, ["credit_amount", "credit", "CREDIT_AMOUNT"], null);
            return {
                ...row,
                account_code: firstValue(row, ["account_code", "ACC_CODE", "accCode", "acc_code"], ""),
                account_name: firstValue(row, ["account_name", "ACC_HEAD", "acc_head", "accHead", "head"], ""),
                counter_account_code: firstValue(row, ["counter_account_code", "REF_ACC_CODE", "refAccCode"], ""),
                counter_account_name: firstValue(row, ["counter_account_name", "ref_acc_head", "refAccHead"], ""),
                description: firstValue(row, ["description", "DESCRIPTION", "notes"], ""),
                debit_amount: debit !== null ? debit : (["D", "DR"].includes(effectiveType) ? amount : 0),
                credit_amount: credit !== null ? credit : (["C", "CR"].includes(effectiveType) ? amount : 0),
                amount,
                show_in_sale_rpt: String(firstValue(row, ["show_in_sale_rpt", "SHOW_IN_SALE_RPT"], "Y")).trim().toUpperCase(),
            };
        });

        const mainRows = items.filter(row => row.show_in_sale_rpt !== "N");
        const systemRows = items.filter(row => row.show_in_sale_rpt === "N");
        const uniqueNames = rows => [...new Set(rows.map(row => String(row.account_name || "").trim()).filter(Boolean))].join(", ");
        const partyName = uniqueNames(mainRows);
        const voucher = payload.voucher || {};
        data.voucher = {
            ...voucher,
            voucher_type: voucherType,
            paid_to: voucher.paid_to || (["CP", "BP"].includes(voucherType) ? partyName : ""),
            paid_from: voucher.paid_from || (["CR", "BR"].includes(voucherType) ? partyName : ""),
            payment_account: voucher.payment_account || uniqueNames(systemRows),
        };
        if (!data.customer.name && voucherType !== "JV" && mainRows.length) {
            data.customer = {
                account_code: mainRows[0].account_code,
                name: mainRows[0].account_name,
                address: "",
                phone: "",
            };
        }

        const totalDebit = items.reduce((sum, row) => sum + numberValue(row.debit_amount), 0);
        const totalCredit = items.reduce((sum, row) => sum + numberValue(row.credit_amount), 0);
        const totals = payload.totals || {};
        data.totals = {
            discount_percent: 0,
            discount_amount: 0,
            delivery_charges: 0,
            gst_percent: 0,
            gst_amount: 0,
            misc_charges: 0,
            cash_received: 0,
            bank_received: 0,
            change_amount: 0,
            ...totals,
            total_items: totals.total_items ?? (mainRows.length || items.length),
            subtotal: totals.subtotal ?? totalDebit,
            net_total: totals.net_total ?? (totalDebit || totalCredit),
            total_debit: totals.total_debit ?? totalDebit,
            total_credit: totals.total_credit ?? totalCredit,
        };
        data.items = items;
        return data;
    }

    function mapLocalPayloadToDocumentData(payload, documentType, billNumber) {
        if (documentType === "voucher") return mapVoucherPayload(payload, billNumber);
        const data = commonDocumentData(payload, documentType, billNumber);
        data.items = (payload.items || []).map(item => {
            const rowNotes = firstValue(item, ["row_notes", "item_notes", "notes"], "");
            const focQty = firstValue(item, ["foc_qty", "foc"], 0);
            const warranty = firstValue(item, ["warranty", "warranty_notes"], rowNotes);
            return {
                ...item,
                product_name: firstValue(item, ["product_name", "prod_name"], ""),
                product_name_ur: firstValue(item, ["product_name_ur", "prod_name_ur"], ""),
                category: firstValue(item, ["category"], ""),
                quantity: firstValue(item, ["quantity", "qty"], ""),
                foc_qty: focQty,
                foc: focQty,
                unit: firstValue(item, ["unit", "uom"], ""),
                packing_mode: firstValue(item, ["packing_mode"], ""),
                pack_quantity: firstValue(item, ["pack_quantity", "pack_qty"], ""),
                rate: firstValue(item, ["rate"], ""),
                discount_percent: firstValue(item, ["discount_percent", "row_discount_percent"], 0),
                discount_amount: firstValue(item, ["discount_amount", "row_discount_amount"], 0),
                amount: firstValue(item, ["amount", "row_net_total"], ""),
                item_notes: rowNotes,
                row_notes: rowNotes,
                warranty,
                warranty_notes: warranty,
                barcode: firstValue(item, ["barcode", "manualbc"], ""),
                brand: firstValue(item, ["brand", "brand_name"], ""),
                cost_price: firstValue(item, ["cost_price", "row_rate_cost"], 0),
                net_cost: firstValue(item, ["net_cost", "row_net_cost"], 0),
            };
        });
        const totals = payload.totals || {};
        data.totals = {
            ...totals,
            total_items: totals.total_items ?? firstValue(payload, ["header_total_items"], ""),
            subtotal: totals.subtotal ?? firstValue(payload, ["header_item_total"], 0),
            discount_percent: totals.discount_percent ?? firstValue(payload, ["header_discount_percent"], 0),
            discount_amount: totals.discount_amount ?? firstValue(payload, ["header_discount_amount"], 0),
            delivery_charges: totals.delivery_charges ?? firstValue(payload, ["header_delivery_charges"], 0),
            gst_percent: totals.gst_percent ?? firstValue(payload, ["header_gst_percent"], 0),
            gst_amount: totals.gst_amount ?? firstValue(payload, ["header_gst_amount"], 0),
            misc_charges: totals.misc_charges ?? firstValue(payload, ["header_misc_charges", "header_msc_charges"], 0),
            net_total: totals.net_total ?? firstValue(payload, ["header_net_total"], 0),
            cash_received: totals.cash_received ?? firstValue(payload, ["header_cash_paid"], 0),
            bank_received: totals.bank_received ?? firstValue(payload, ["header_bank_paid"], 0),
            change_amount: totals.change_amount ?? firstValue(payload, ["header_change_amount"], 0),
        };
        return data;
    }

    function mergeCachedCompanyData(documentData, cached) {
        if (!cached) return documentData;
        for (const section of ["company", "branch"]) {
            const merged = { ...(cached[section] || {}) };
            for (const [key, value] of Object.entries(documentData[section] || {})) {
                if (value !== undefined && value !== null && value !== "") merged[key] = value;
            }
            documentData[section] = merged;
        }
        return documentData;
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, options);
        if (!response.ok) {
            const body = await response.text();
            throw new Error(`DocumentPrinter request failed (${response.status}): ${body}`);
        }
        return response.json();
    }

    async function getLocalTemplateConfig(documentType, pageType) {
        if (!window.IndexDBConfig?.get_record) return null;
        return window.IndexDBConfig.get_record("template_configs", `${documentType}_${pageType}`);
    }

    async function saveBasicTemplateConfig(documentType, pageType, configuration, updatedAt) {
        if (!window.IndexDBConfig?.save_update_record) return;
        await window.IndexDBConfig.save_update_record("template_configs", {
            key: `${documentType}_${pageType}`,
            document_type: documentType,
            page_type: pageType,
            configuration,
            updated_at: updatedAt || new Date().toISOString(),
        });
    }

    async function getOfflineTemplateBundle(documentType, pageType, overrides = {}) {
        if (!window.OfflineTemplateEngine?.renderFromCache) {
            throw new Error("OfflineTemplateEngine is not loaded; local rendering cannot fall back to the server");
        }
        const record = overrides.configuration ? {
            configuration: overrides.configuration,
            registry: overrides.registry,
            company_data: overrides.companyData,
            css: overrides.cssText,
        } : await getLocalTemplateConfig(documentType, pageType);
        if (!record?.configuration) {
            throw new Error(`No offline template is saved for ${documentType}/${pageType}. Open the designer online and click Save Template once.`);
        }
        const [registry, companyData, css] = await Promise.all([
            record.registry || window.OfflineTemplateEngine.getCachedRegistry(),
            record.company_data || window.OfflineTemplateEngine.getCachedCompanyData(),
            record.css || window.OfflineTemplateEngine.getCachedStylesheet(),
        ]);
        if (!registry?.fields) {
            throw new Error("The offline field registry is missing. Save this template again while online.");
        }
        return { configuration: record.configuration, registry, companyData, css };
    }

    // Online configuration lookup, used only when rendering_source=server.
    async function loadConfiguration(documentType, pageType) {
        const cached = await getLocalTemplateConfig(documentType, pageType);
        if (cached?.configuration) return cached.configuration;
        const query = new URLSearchParams({ document_type: documentType, page_type: pageType });
        const data = await fetchJson(`${ENDPOINTS.configuration}?${query}`);
        if (!data.configuration) throw new Error("The server returned no template configuration");
        await saveBasicTemplateConfig(documentType, pageType, data.configuration, data.updated_at);
        return data.configuration;
    }

    async function loadServerDocumentData(options) {
        const query = new URLSearchParams({
            document_type: options.documentType,
            model_name: options.modelName || "",
            bill_number: options.billNumber ?? "",
            page_type: options.pageType || "",
        });
        return fetchJson(`${ENDPOINTS.documentData}?${query}`);
    }

    async function renderOnServer(configuration, documentData) {
        const data = await fetchJson(ENDPOINTS.render, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ configuration, document_data: documentData }),
        });
        return data.html;
    }

    async function ensureStylesheet(cssText, renderSource) {
        const existing = document.querySelector(
            "link[data-document-printer-css], style[data-document-printer-css], link[href*='invoice_designer/css/designer']"
        );
        if (existing) return;
        if (cssText) {
            const style = document.createElement("style");
            style.dataset.documentPrinterCss = "true";
            style.textContent = cssText;
            document.head.appendChild(style);
            return;
        }
        if (renderSource === "local") {
            throw new Error("Offline print CSS is missing. Save this template again while online.");
        }
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = "/static/invoice_designer/css/designer.css";
        link.dataset.documentPrinterCss = "true";
        document.head.appendChild(link);
    }

    async function ensureModal(cssText, renderSource) {
        await ensureStylesheet(cssText, renderSource);
        let overlay = document.getElementById("print-modal-overlay");
        if (!overlay) {
            const holder = document.createElement("div");
            holder.innerHTML = `
                <div class="print-modal-overlay" id="print-modal-overlay">
                    <div class="print-modal">
                        <div class="print-modal-toolbar no-print">
                            <select id="print-modal-page-type"></select>
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
        }

        const select = document.getElementById("print-modal-page-type");
        select.innerHTML = PAGE_TYPES.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
        if (!overlay.dataset.documentPrinterBound) {
            document.getElementById("print-modal-close-button").addEventListener("click", closePreviewModal);
            document.getElementById("print-modal-print-button").addEventListener("click", () => window.print());
            select.addEventListener("change", () => renderIntoModal(select.value).catch(() => {}));
            overlay.dataset.documentPrinterBound = "true";
        }
        return overlay;
    }

    function showModalError(error, directprint) {
        const overlay = document.getElementById("print-modal-overlay");
        const page = document.getElementById("print-modal-page");
        if (!overlay || !page) return;
        const message = String(error?.message || error).replace(/[&<>"']/g, character => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        })[character]);
        page.innerHTML = `<div style="padding:20px;max-width:560px;color:#b42318;font:13px/1.5 Arial"><b>Print could not be rendered</b><br>${message}</div>`;
        overlay.classList.toggle("open", !directprint);
    }

    async function renderIntoModal(pageType) {
        const options = { ...modalState, pageType };
        let configuration;
        let documentData;
        let html;
        let css = "";

        try {
            if (options.renderSource === "local") {
                if (options.dataSource === "server") {
                    const [bundle, result] = await Promise.all([
                        getOfflineTemplateBundle(options.documentType, pageType, options),
                        loadServerDocumentData(options),
                    ]);
                    configuration = bundle.configuration;
                    documentData = result.document_data;
                    css = bundle.css;
                    mergeCachedCompanyData(documentData, bundle.companyData);
                    html = window.OfflineTemplateEngine.renderFromCache(configuration, documentData, bundle.registry);
                } else {
                    const bundle = await getOfflineTemplateBundle(options.documentType, pageType, options);
                    configuration = bundle.configuration;
                    documentData = mapLocalPayloadToDocumentData(options.payload, options.documentType, options.billNumber);
                    css = bundle.css;
                    mergeCachedCompanyData(documentData, bundle.companyData);
                    html = window.OfflineTemplateEngine.renderFromCache(configuration, documentData, bundle.registry);
                }
            } else if (options.dataSource === "server") {
                const result = await loadServerDocumentData(options);
                documentData = result.document_data;
                configuration = options.configuration || result.template_config || await loadConfiguration(options.documentType, pageType);
                html = await renderOnServer(configuration, documentData);
            } else {
                configuration = options.configuration || await loadConfiguration(options.documentType, pageType);
                documentData = mapLocalPayloadToDocumentData(options.payload, options.documentType, options.billNumber);
                html = await renderOnServer(configuration, documentData);
            }

            const overlay = await ensureModal(css, options.renderSource);
            const page = document.getElementById("print-modal-page");
            page.innerHTML = html;
            page.dataset.pageType = pageType;
            document.getElementById("print-modal-page-type").value = pageType;
            overlay.classList.toggle("open", !options.directprint);
            return html;
        } catch (error) {
            showModalError(error, options.directprint);
            throw error;
        }
    }

    async function openPreviewModal(rawOptions) {
        const options = normalizeOptions(rawOptions);
        validateOptions(options);
        modalState = options;
        return renderIntoModal(options.pageType);
    }

    function closePreviewModal() {
        document.getElementById("print-modal-overlay")?.classList.remove("open");
    }

    window.addEventListener("keydown", event => {
        if (event.key === "Escape") closePreviewModal();
    });

    async function printDocument(rawOptions) {
        const options = normalizeOptions(rawOptions);
        validateOptions(options);
        const html = await openPreviewModal(rawOptions);
        const copies = options.allowMultiplePrint ? Math.max(1, parseInt(options.copies, 10) || 1) : 1;
        if (copies > 1) {
            document.getElementById("print-modal-page").innerHTML = Array.from(
                { length: copies }, () => `<div class="print-copy">${html}</div>`
            ).join("");
        }
        if (options.directprint) window.print();
        return html;
    }

    return { printDocument, openPreviewModal, closePreviewModal };
})();
