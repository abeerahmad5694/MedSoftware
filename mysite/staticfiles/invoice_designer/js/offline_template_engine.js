/**
 * OfflineTemplateEngine
 * ─────────────────────
 * A faithful JavaScript port of:
 *   • services/renderer.py  (DocumentRenderer.render)
 *   • document_template.html
 *   • schema.py             (style resolution, page dimensions)
 *
 * Produces byte-for-byte compatible HTML with the Python server —
 * same CSS class names, same data-field attributes, same inline styles,
 * same Urdu/bilingual layout, same hide_if_zero / always_show logic.
 *
 * All rendering is synchronous after data is resolved.
 * The only async calls are for IndexedDB access (preload/cache).
 */
window.OfflineTemplateEngine = (function () {
  "use strict";

  // ── Page dimensions (mirrors schema.PAGE_DIMENSIONS_MILLIMETERS) ─────────
  const PAGE_DIMENSIONS = {
    thermal_58:    { width: 58,  height: null },
    thermal_80:    { width: 80,  height: null },
    a5:            { width: 148, height: 210  },
    a4:            { width: 210, height: 297  },
    urdu_58mm:     { width: 58,  height: null },
    urdu_80mm:     { width: 80,  height: null },
    urdu_a4:       { width: 210, height: 297  },
    urdu_a5:       { width: 148, height: 210  },
    bilingual_a4:  { width: 210, height: 297  },
    bilingual_80mm:{ width: 80,  height: null },
  };

  // ── Style resolution (mirrors schema.resolve_style + style_dict_to_css) ──
  const DEFAULT_STYLE_BASE = {
    font_family: "Arial", font_size: 12, bold: false, italic: false,
    underline: false, alignment: "left", text_color: "#1a1a1a",
    background_color: "transparent", border: "none",
    padding: "2px 0", margin: "0", width: "auto",
  };

  const STYLE_PRESETS = {
    normal: {},
    small: { font_size: 10 },
    muted_small: { font_size: 10, text_color: "#4a4a4a" },
    heading: { font_size: 16, bold: true },
    title: { font_size: 14, bold: true, alignment: "center" },
    bold_total: { font_size: 14, bold: true },
    center: { alignment: "center" },
    center_small: { font_size: 11, alignment: "center" },
    tiny: { font_size: 8 },
    tiny_center: { font_size: 8, alignment: "center" },
    logo: { width: "70px" },
    urdu_normal:     { font_family: "Jameel Noori Nastaleeq", alignment: "right" },
    urdu_heading:    { font_family: "Jameel Noori Nastaleeq", font_size: 18, bold: true, alignment: "center" },
    urdu_title:      { font_family: "Jameel Noori Nastaleeq", font_size: 16, bold: true, alignment: "center" },
    urdu_small:      { font_family: "Jameel Noori Nastaleeq", font_size: 10, alignment: "right" },
    urdu_tiny:       { font_family: "Jameel Noori Nastaleeq", font_size: 8,  alignment: "right" },
    urdu_bold_total: { font_family: "Jameel Noori Nastaleeq", font_size: 14, bold: true, alignment: "right" },
    urdu_center_small:{ font_family: "Jameel Noori Nastaleeq", font_size: 11, alignment: "center" },
  };

  // Default page margins (mm) — mirrors schema defaults
  const DEFAULT_PAGE = { margin_top_mm: 4, margin_right_mm: 4, margin_bottom_mm: 4, margin_left_mm: 4 };

  // TOTALS data_source sub-key map (mirrors TOTALS_REGISTRY.data_source)
  const TOTALS_DATA_SOURCE = {
    total_items:     "total_items",
    subtotal:        "subtotal",
    discount:        "discount_amount",
    gst:             "gst_amount",
    delivery_charges:"delivery_charges",
    misc_charges:    "misc_charges",
    net_total:       "net_total",
    total_debit:     "total_debit",
    total_credit:    "total_credit",
    cash_received:   "cash_received",
    bank_received:   "bank_received",
    change_amount:   "change_amount",
    previous_balance:"previous_balance",
    current_balance: "current_balance",
  };
  const ZERO_ALWAYS_VISIBLE = new Set(["net_total", "subtotal"]);

  // Urdu column labels (mirrors schema.URDU_COLUMN_LABELS)
  const URDU_COLUMN_LABELS = {
    product_name: "مال", category: "قسم", quantity: "مقدار",
    unit: "یونٹ", rate: "قیمت", discount_percent: "چھوٹ%",
    discount_amount: "چھوٹ", amount: "رقم", item_notes: "نوٹ",
    subtotal: "کل رقم", discount: "چھوٹ", gst: "ٹیکس",
    delivery_charges: "ڈیلیوری", misc_charges: "دیگر",
    net_total: "کل قابل ادا", cash_received: "نقد وصول",
    bank_received: "بینک وصول", change_amount: "واپسی",
    total_debit: "کل ڈیبٹ", total_credit: "کل کریڈٹ",
    account_code: "اکاؤنٹ کوڈ", account_name: "اکاؤنٹ کا نام",
    counter_account_code: "مقابل اکاؤنٹ کوڈ", counter_account_name: "مقابل اکاؤنٹ کا نام",
    debit_amount: "ڈیبٹ", credit_amount: "کریڈٹ",
    paid_to: "ادا کیا گیا کو", paid_from: "وصول شدہ از", payment_account: "کیش / بینک اکاؤنٹ",
    previous_balance: "پچھلا بقایا", current_balance: "موجودہ بقایا",
    customer_name: "نام", customer_address: "پتہ",
    customer_phone: "فون", customer_account: "کوڈ",
  };

  // ── Helpers ───────────────────────────────────────────────────────────────

  function resolveStyle(name, overrides) {
    const base = Object.assign({}, DEFAULT_STYLE_BASE, STYLE_PRESETS[name] || {});
    if (overrides && typeof overrides === "object") Object.assign(base, overrides);
    return base;
  }

  function styleToCss(style) {
    if (!style) return "";
    const parts = [];
    if (style.font_family) parts.push(`font-family: ${style.font_family};`);
    if (style.font_size)   parts.push(`font-size: ${style.font_size}px;`);
    parts.push(style.bold ? "font-weight: bold;" : "font-weight: normal;");
    if (style.italic)     parts.push("font-style: italic;");
    if (style.underline)  parts.push("text-decoration: underline;");
    if (style.alignment)  parts.push(`text-align: ${style.alignment};`);
    if (style.text_color) parts.push(`color: ${style.text_color};`);
    if (style.background_color && style.background_color !== "transparent")
      parts.push(`background-color: ${style.background_color};`);
    if (style.border && style.border !== "none") parts.push(`border: ${style.border};`);
    if (style.padding) parts.push(`padding: ${style.padding};`);
    if (style.margin)  parts.push(`margin: ${style.margin};`);
    if (style.width && style.width !== "auto") parts.push(`width: ${style.width};`);
    return parts.join(" ");
  }

  function resolveFieldStyleCss(fieldConf) {
    return styleToCss(resolveStyle(fieldConf.style || "normal", fieldConf.style_overrides));
  }

  function isZero(val) {
    if (val === null || val === undefined || val === "" || val === "N/A") return true;
    try { return parseFloat(String(val).replace(/,/g, "")) === 0.0; }
    catch { return false; }
  }

  function formatNumber(val) {
    if (val === null || val === undefined || val === "") return val;
    const cleaned = typeof val === "string" ? val.replace(/,/g, "") : val;
    const f = parseFloat(cleaned);
    if (isNaN(f)) return val;
    return parseFloat(f.toFixed(2)).toString();
  }

  function toCssUnit(val) {
    if (!val) return "";
    const s = String(val).trim();
    return /^\d+$/.test(s) ? `${s}px` : s;
  }

  /** Resolve a value from documentData using a dot-path like "company.name" */
  function getByPath(data, path) {
    if (!path) return null;
    let node = data;
    for (const key of path.split(".")) {
      if (!node || typeof node !== "object") return null;
      node = node[key];
    }
    return node ?? null;
  }

  /** Mirrors renderer._resolve_field_value */
  function resolveFieldValue(fieldKey, fieldConf, registryEntry, documentData) {
    // Priority 1: field_overrides in document_data
    const overrides = (documentData || {}).field_overrides || {};
    if (fieldKey in overrides) return overrides[fieldKey];

    // Priority 2: custom_value in field config
    const custom = fieldConf.custom_value;
    if (custom !== null && custom !== undefined && custom !== "") return custom;

    // Priority 3: static_text
    if (registryEntry && registryEntry.field_type === "static_text") {
      return registryEntry.static_text || "";
    }

    // Priority 4: data_source from registry
    const dataSource = registryEntry && registryEntry.data_source;
    if (dataSource) {
      const v = getByPath(documentData || {}, dataSource);
      if (v !== null && v !== undefined && v !== "") return v;
    }

    return "";
  }

  function applyPrefixSuffix(value, fieldConf) {
    const prefix = fieldConf.prefix || "";
    const suffix = fieldConf.suffix || "";
    if (prefix || suffix) return `${prefix}${value}${suffix}`;
    return value;
  }

  /** Build format_key → field_key alias map for format_string resolution */
  const FORMAT_KEY_TO_FIELD = {};
  // Populated at init from registry (called after preload)

  function resolveFormatString(fmt, rowDict) {
    return fmt.replace(/\{(\w+)\}/g, (_, k) => {
      // Try direct key first, then alias
      if (rowDict[k] !== undefined) return String(rowDict[k] ?? "");
      const fieldKey = FORMAT_KEY_TO_FIELD[k];
      if (fieldKey && rowDict[fieldKey] !== undefined) return String(rowDict[fieldKey] ?? "");
      return "";
    });
  }

  function isUrduPageType(pt) {
    return pt && (pt.startsWith("urdu_") || pt === "urdu_a4" || pt === "urdu_a5");
  }
  function isBilingualPageType(pt) {
    return pt && pt.startsWith("bilingual_");
  }

  // ── Section resolvers (mirrors renderer.py) ───────────────────────────────

  function resolveFieldSection(sectionKey, sectionConfig, documentData, registry) {
    // exclude_accounts check
    if (sectionKey === "customer" && sectionConfig.exclude_accounts) {
      const cust = documentData.customer || {};
      const cName = String(cust.name ?? "").strip ? String(cust.name ?? "").toLowerCase() : String(cust.name ?? "").toLowerCase();
      const cCode = String(cust.account_code ?? "").toLowerCase();
      const excluded = String(sectionConfig.exclude_accounts)
        .split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
      if (excluded.some(ex => cName === ex || cCode === ex)) return [];
    }

    const fieldRegistry = (registry && registry.fields) || {};
    const resolved = [];

    for (const fieldConf of (sectionConfig.fields || [])) {
      if (fieldConf.visible === false) continue;
      const fieldKey = fieldConf.field;
      const reg = fieldRegistry[fieldKey] || { field_type: "text", data_source: null };

      if (reg.field_type === "image") {
        const url = fieldConf.custom_value
          || getByPath(documentData, reg.data_source || "")
          || "";
        if (!url) continue;
        resolved.push({
          field: fieldKey,
          type: "image",
          value: url,
          value_ur: "",
          style_css: resolveFieldStyleCss(fieldConf),
          logo_width: toCssUnit(fieldConf.logo_width),
          logo_height: toCssUnit(fieldConf.logo_height),
        });
        continue;
      }

      let value = resolveFieldValue(fieldKey, fieldConf, reg, documentData);
      let value_ur = "";
      if (reg.data_source) {
        value_ur = getByPath(documentData, reg.data_source + "_ur") || "";
      }
      value = applyPrefixSuffix(value, fieldConf);
      if (value_ur) value_ur = applyPrefixSuffix(value_ur, fieldConf);

      // Auto-hide empty fields
      if (value === "" && value_ur === "") continue;

      const label = fieldConf.label || reg.label || fieldKey;
      resolved.push({
        field: fieldKey,
        label,
        value,
        value_ur,
        type: reg.field_type || "text",
        style_css: resolveFieldStyleCss(fieldConf),
        logo_width: "",
        logo_height: "",
      });
    }
    return resolved;
  }

  function resolveItemColumns(itemsConfig, allItems, documentType, registry) {
    const itemRegistry = (registry && registry.item_columns_by_document_type && registry.item_columns_by_document_type[documentType]) || {};
    const columns = (itemsConfig.columns || []).filter(c => c.visible !== false);
    columns.sort((a, b) => (a.order || 0) - (b.order || 0));
    const resolved = [];
    for (const col of columns) {
      const fieldKey = col.field;
      const reg = itemRegistry[fieldKey] || {};
      // Auto-hide all-zero columns
      if (!col.always_show && allItems && allItems.length > 0) {
        const allZero = allItems.every(row => {
          const v = (typeof row === "object") ? row[fieldKey] : undefined;
          return isZero(v);
        });
        if (allZero) continue;
      }
      resolved.push({
        field: fieldKey,
        label: col.label || reg.label || fieldKey,
        default_label: reg.label || fieldKey,
        width: col.width || reg.default_width || "auto",
        style_css: resolveFieldStyleCss(col),
        format_string: col.format_string || null,
      });
    }
    return resolved;
  }

  function resolveItemRows(visibleColumns, documentData) {
    const rows = (documentData && documentData.items) || [];
    return rows.map(row => {
      // Format all numbers
      const rowDict = {};
      for (const [k, v] of Object.entries(row)) {
        rowDict[k] = formatNumber(v) ?? v;
      }
      return visibleColumns.map(col => {
        let cellVal;
        if (col.format_string) {
          try { cellVal = resolveFormatString(col.format_string, rowDict); }
          catch { cellVal = String(rowDict[col.field] ?? ""); }
        } else {
          cellVal = String(rowDict[col.field] ?? "");
        }
        return { value: cellVal, style_css: col.style_css, field: col.field };
      });
    });
  }

  function resolveTotals(totalsConfig, documentData) {
    const totalsData = Object.assign({}, (documentData && documentData.totals) || {});
    // Compute current_balance if missing
    if (!("current_balance" in totalsData) && "previous_balance" in totalsData) {
      const received = parseFloat(totalsData.cash_received || 0) + parseFloat(totalsData.bank_received || 0);
      totalsData.current_balance = Math.round((
        parseFloat(totalsData.previous_balance || 0)
        + parseFloat(totalsData.net_total || 0)
        - received
      ) * 100) / 100;
    }

    const fields = (totalsConfig.fields || []).filter(f => f.visible !== false);
    fields.sort((a, b) => (a.order || 0) - (b.order || 0));

    const resolved = [];
    for (const fieldConf of fields) {
      const key = fieldConf.field;
      const subKey = TOTALS_DATA_SOURCE[key] || key;
      const value = totalsData[subKey] ?? 0;

      const hideIfZero = fieldConf.hide_if_zero !== false; // default true
      if (hideIfZero && !ZERO_ALWAYS_VISIBLE.has(key) && isZero(value)) continue;

      const reg = (documentData.__totalsRegistry || {})[key] || {};
      resolved.push({
        field: key,
        label: fieldConf.label || reg.label || key,
        value: formatNumber(value),
        style_css: resolveFieldStyleCss(fieldConf),
      });
    }
    return resolved;
  }

  // ── HTML building (mirrors document_template.html) ───────────────────────

  function e(v) {
    // HTML-escape
    return String(v ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function buildImageTag(field, isUrdu) {
    const w = field.logo_width ? `width:${field.logo_width};` : "max-width:100%;";
    const h = field.logo_height ? `height:${field.logo_height};` : "";
    return `<div class="doc-field" data-field="header:${e(field.field)}" style="${e(field.style_css)}">` +
      `<img src="${e(field.value)}" alt="Logo" style="${w}${h}object-fit:contain;" onerror="this.style.display='none'">` +
      `</div>`;
  }

  /**
   * Main entry point — mirrors DocumentRenderer.render()
   * @param {object} configuration  Template configuration JSON
   * @param {object} documentData   Document data (invoice, items, totals)
   * @param {object|null} registry  Field registry from IndexedDB
   * @returns {string}  HTML string
   */
  function renderFromCache(configuration, documentData, registry) {
    if (!configuration || !configuration.sections) {
      throw new Error("OfflineTemplateEngine: a saved template configuration is required");
    }
    documentData = documentData || {};
    populateFormatAliases(registry);
    const sections = configuration.sections || {};
    const pageType = configuration.page_type || "thermal_80";
    const docType  = configuration.document_type || "pos_invoice";

    const isUrdu = isUrduPageType(pageType) ||
                   (configuration.invoice_language === "urdu");
    const isBilingual = isBilingualPageType(pageType) ||
                        (configuration.invoice_language === "bilingual");
    const hasUrdu = isUrdu || isBilingual;

    // Page
    const dims   = PAGE_DIMENSIONS[pageType] || PAGE_DIMENSIONS.thermal_80;
    const styles = configuration.styles || {};
    const pg     = Object.assign({}, DEFAULT_PAGE, configuration.page || {});
    const defaultFont = styles.default_font_family || "Arial";
    const defaultSize = styles.default_font_size || 12;

    const colLabelsUr = configuration.column_labels_ur || URDU_COLUMN_LABELS;

    // Resolve sections. Voucher row filtering is deliberately done here (and
    // in renderer.py) so server and local output make the same template choice.
    let rawItems = documentData.items || [];
    if (docType === "voucher") {
      const rowFilter = (sections.items || {}).row_filter || "main";
      if (rowFilter === "main" || rowFilter === "system") {
        rawItems = rawItems.filter(row => {
          const isMain = String(row.show_in_sale_rpt || "Y").trim().toUpperCase() !== "N";
          return isMain === (rowFilter === "main");
        });
      }
    }
    const rowDocumentData = Object.assign({}, documentData, { items: rawItems });
    const headerFields   = resolveFieldSection("header",   sections.header   || { fields: [] }, documentData, registry);
    const customerFields = resolveFieldSection("customer", sections.customer || { fields: [] }, documentData, registry);
    const footerFields   = resolveFieldSection("footer",   sections.footer   || { fields: [] }, documentData, registry);
    const visibleColumns = resolveItemColumns(sections.items || { columns: [] }, rawItems, docType, registry);
    const plainRows      = resolveItemRows(visibleColumns, rowDocumentData);
    const totalFields    = resolveTotals(sections.totals || { fields: [] }, documentData);
    const tableBorders   = (sections.items || {}).table_borders ? " has-borders" : "";
    const itemsVisible   = (sections.items || {}).visible !== false;
    const totalsVisible  = (sections.totals || {}).visible !== false;
    const headerVisible  = (sections.header || {}).visible !== false;
    const customerVisible= (sections.customer || {}).visible !== false;
    const footerVisible  = (sections.footer || {}).visible !== false;

    // Build rows_with_urdu
    const rowsWithUrdu = rawItems.map((row, idx) => {
      const pname_ur = (typeof row === "object" ? row.product_name_ur : "") || "";
      const cells = plainRows[idx] || [];
      return { cells, product_name_ur: pname_ur };
    });

    // ── Page style string ──────────────────────────────────────────────────
    const wrapStyle = [
      `width: ${dims.width}mm;`,
      dims.height ? `min-height: ${dims.height}mm;` : "",
      `padding: ${pg.margin_top_mm || 4}mm ${pg.margin_right_mm || 4}mm ${pg.margin_bottom_mm || 4}mm ${pg.margin_left_mm || 4}mm;`,
      `font-family: ${defaultFont}${hasUrdu ? ", 'Noto Nastaliq Urdu', serif" : ""};`,
      `font-size: ${defaultSize}px;`,
    ].filter(Boolean).join(" ");

    let html = "";

    if (hasUrdu) {
      // ════════════════════════════ URDU / BILINGUAL ═══════════════════════
      html += `<div class="printable-document${isUrdu ? " urdu-doc" : ""}${isBilingual ? " bilingual-doc" : ""}" ` +
        `data-page-type="${e(pageType)}" data-document-type="${e(docType)}" ` +
        `${isUrdu ? 'dir="rtl" lang="ur"' : ""} style="${e(wrapStyle)}">`;

      // Header
      if (headerVisible) {
        html += `<div class="doc-section doc-header${isUrdu ? " urdu-section" : ""}" data-section="header"${isUrdu ? ' dir="rtl" lang="ur"' : ""}>`;
        if (isBilingual) {
          html += `<table class="bilingual-header-table" style="width:100%;border-collapse:collapse;"><tr>`;
          html += `<td style="width:50%;vertical-align:top;padding-right:6px;">`;
          for (const field of headerFields) {
            if (field.type === "image") { html += buildImageTag(field, false); }
            else html += `<div class="doc-field" data-field="header:${e(field.field)}" style="${e(field.style_css)}">${e(field.value)}</div>`;
          }
          html += `</td><td style="width:50%;vertical-align:top;text-align:right;padding-left:6px;" dir="rtl" lang="ur">`;
          for (const field of headerFields) {
            if (field.type !== "image") {
              html += `<div class="doc-field urdu-font" data-field="header:${e(field.field)}_ur" style="${e(field.style_css)}">${e(field.value_ur || field.value)}</div>`;
            }
          }
          html += `</td></tr></table>`;
        } else {
          // Pure Urdu
          for (const field of headerFields) {
            if (field.type === "image") { html += buildImageTag(field, true); }
            else html += `<div class="doc-field urdu-font" data-field="header:${e(field.field)}" style="${e(field.style_css)}">${e(field.value_ur || field.value)}</div>`;
          }
        }
        html += `</div>`;
      }

      // Customer
      if (customerVisible && customerFields.length) {
        html += `<div class="doc-section doc-customer${isUrdu ? " urdu-section" : ""}" data-section="customer"${isUrdu ? ' dir="rtl" lang="ur"' : ""}>`;
        for (const field of customerFields) {
          if (isBilingual) {
            const urLabel = colLabelsUr[field.field] || field.label;
            const urVal = field.value_ur || field.value;
            html += `<div class="doc-field bilingual-customer-row" data-field="customer:${e(field.field)}" style="${e(field.style_css)}">` +
              `<span>${e(field.label)}${field.value ? ": " + e(field.value) : ""}</span>` +
              `<span class="urdu-font" dir="rtl" lang="ur" style="float:left;">${e(urLabel)}${urVal ? ": " + e(urVal) : ""}</span>` +
              `</div>`;
          } else {
            const urLabel = colLabelsUr[field.field] || field.label;
            const urVal = field.value_ur || field.value;
            html += `<div class="doc-field urdu-font" data-field="customer:${e(field.field)}" style="${e(field.style_css)}">` +
              `${e(urLabel)}${urVal ? ": " + e(urVal) : ""}` +
              `</div>`;
          }
        }
        html += `</div>`;
      }

      // Items
      if (itemsVisible) {
        html += `<div class="doc-section doc-items${isUrdu ? " urdu-section" : ""}" data-section="items">`;
        html += `<table class="doc-item-table${tableBorders}"${isUrdu ? ' dir="rtl" lang="ur"' : ""}><thead><tr>`;
        for (const col of visibleColumns) {
          const urLabel = colLabelsUr[col.field] || col.label;
          if (isBilingual) {
            html += `<th data-field="items:column:${e(col.field)}" style="width: ${e(col.width)}; ${e(col.style_css)}">` +
              `<span>${e(col.label)}</span><br>` +
              `<span class="urdu-font" dir="rtl" lang="ur" style="font-size:0.85em;">${e(urLabel)}</span></th>`;
          } else {
            html += `<th data-field="items:column:${e(col.field)}" class="urdu-font" style="width: ${e(col.width)}; ${e(col.style_css)}">${e(urLabel)}</th>`;
          }
        }
        html += `</tr></thead><tbody>`;
        if (rowsWithUrdu.length === 0) {
          html += `<tr><td colspan="${visibleColumns.length}" class="doc-empty-row urdu-font">کوئی آئٹم نہیں</td></tr>`;
        } else {
          for (const rowData of rowsWithUrdu) {
            html += `<tr>`;
            for (const cell of rowData.cells) {
              html += `<td style="${e(cell.style_css)}">`;
              if (isBilingual && cell.field === "product_name") {
                html += `<span>${e(cell.value)}</span><br>`;
                const ur = rowData.product_name_ur || cell.value;
                html += `<span class="urdu-font" dir="rtl" lang="ur" style="font-size:0.85em;display:block;text-align:right;">${e(ur)}</span>`;
              } else if (isUrdu && cell.field === "product_name") {
                const ur = rowData.product_name_ur || cell.value;
                html += `<span class="urdu-font" dir="rtl" lang="ur" style="display:block;text-align:right;">${e(ur)}</span>`;
              } else {
                html += e(cell.value);
              }
              html += `</td>`;
            }
            html += `</tr>`;
          }
        }
        html += `</tbody></table></div>`;
      }

      // Totals
      if (totalsVisible) {
        html += `<div class="doc-section doc-totals${isUrdu ? " urdu-section" : ""}" data-section="totals"${isUrdu ? ' dir="rtl" lang="ur"' : ""}>`;
        for (const field of totalFields) {
          html += `<div class="doc-field doc-total-row${isUrdu ? " urdu-total-row" : ""}" data-field="totals:${e(field.field)}" style="${e(field.style_css)}">`;
          if (isBilingual) {
            const urLabel = colLabelsUr[field.field] || field.label;
            html += `<span class="urdu-font" dir="rtl" lang="ur">${e(urLabel)}</span><span>${e(field.value ?? "0")}</span><span>${e(field.label)}</span>`;
          } else if (isUrdu) {
            const urLabel = colLabelsUr[field.field] || field.label;
            html += `<span class="urdu-font">${e(urLabel)}</span><span>${e(field.value ?? "0")}</span>`;
          } else {
            html += `<span>${e(field.label)}</span><span>${e(field.value ?? "0")}</span>`;
          }
          html += `</div>`;
        }
        html += `</div>`;
      }

      // Footer
      if (footerVisible && footerFields.length) {
        html += `<div class="doc-section doc-footer${isUrdu ? " urdu-section" : ""}" data-section="footer"${isUrdu ? ' dir="rtl" lang="ur"' : ""}>`;
        for (const field of footerFields) {
          const displayVal = colLabelsUr[field.field] || field.value;
          html += `<div class="doc-field${isUrdu ? " urdu-font" : ""}" data-field="footer:${e(field.field)}" style="${e(field.style_css)}">${e(displayVal)}</div>`;
        }
        html += `</div>`;
      }

      html += `</div>`;

    } else {
      // ════════════════════════════ ENGLISH ════════════════════════════════
      html += `<div class="printable-document" data-page-type="${e(pageType)}" data-document-type="${e(docType)}" style="${e(wrapStyle)}">`;

      // Header
      if (headerVisible) {
        html += `<div class="doc-section doc-header" data-section="header">`;
        for (const field of headerFields) {
          if (field.type === "image") { html += buildImageTag(field, false); }
          else html += `<div class="doc-field" data-field="header:${e(field.field)}" style="${e(field.style_css)}">${e(field.value)}</div>`;
        }
        html += `</div>`;
      }

      // Customer
      if (customerVisible && customerFields.length) {
        html += `<div class="doc-section doc-customer" data-section="customer">`;
        for (const field of customerFields) {
          html += `<div class="doc-field" data-field="customer:${e(field.field)}" style="${e(field.style_css)}">${e(field.label)}${field.value ? ": " + e(field.value) : ""}</div>`;
        }
        html += `</div>`;
      }

      // Items
      if (itemsVisible) {
        html += `<div class="doc-section doc-items" data-section="items">`;
        html += `<table class="doc-item-table${tableBorders}"><thead><tr>`;
        for (const col of visibleColumns) {
          html += `<th data-field="items:column:${e(col.field)}" style="width: ${e(col.width)}; ${e(col.style_css)}">${e(col.label)}</th>`;
        }
        html += `</tr></thead><tbody>`;
        if (plainRows.length === 0) {
          html += `<tr><td colspan="${visibleColumns.length}" class="doc-empty-row">No items</td></tr>`;
        } else {
          for (const row of plainRows) {
            html += `<tr>`;
            for (const cell of row) {
              html += `<td style="${e(cell.style_css)}">${e(cell.value)}</td>`;
            }
            html += `</tr>`;
          }
        }
        html += `</tbody></table></div>`;
      }

      // Totals
      if (totalsVisible) {
        html += `<div class="doc-section doc-totals" data-section="totals">`;
        for (const field of totalFields) {
          html += `<div class="doc-field doc-total-row" data-field="totals:${e(field.field)}" style="${e(field.style_css)}">` +
            `<span>${e(field.label)}</span><span>${e(field.value ?? "0")}</span></div>`;
        }
        html += `</div>`;
      }

      // Footer
      if (footerVisible && footerFields.length) {
        html += `<div class="doc-section doc-footer" data-section="footer">`;
        for (const field of footerFields) {
          html += `<div class="doc-field" data-field="footer:${e(field.field)}" style="${e(field.style_css)}">${e(field.value)}</div>`;
        }
        html += `</div>`;
      }

      html += `</div>`;
    }

    return html;
  }

  // ── IndexedDB helpers ─────────────────────────────────────────────────────

  async function idbGet(store, key) {
    try {
      if (window.IndexDBConfig && typeof window.IndexDBConfig.get_record === "function")
        return await window.IndexDBConfig.get_record(store, key);
    } catch { /* not fatal */ }
    return null;
  }

  async function idbSet(store, record) {
    try {
      if (window.IndexDBConfig && typeof window.IndexDBConfig.save_update_record === "function")
        await window.IndexDBConfig.save_update_record(store, record);
    } catch { /* not fatal */ }
  }

  function cloneJson(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function populateFormatAliases(registry) {
    const registries = registry?.item_columns_by_document_type || {};
    for (const columns of Object.values(registries)) {
      for (const [fieldKey, entry] of Object.entries(columns || {})) {
        if (entry.format_key) FORMAT_KEY_TO_FIELD[entry.format_key] = fieldKey;
      }
    }
  }

  async function urlToBase64(url) {
    if (!url || String(url).startsWith("data:")) return url || "";
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not cache image (${response.status}): ${url}`);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error(`Could not read image: ${url}`));
      reader.readAsDataURL(blob);
    });
  }

  function normalizeStylesheet(cssText) {
    // A cached <style> resolves relative URLs against the page, not the original
    // stylesheet. Make font URLs absolute before storing the CSS.
    return String(cssText || "").replaceAll("../fonts/", "/static/invoice_designer/fonts/");
  }

  async function embedTemplateAssets(configuration, companyData, registry) {
    const config = cloneJson(configuration);
    const company = cloneJson(companyData) || { company: {}, branch: {} };
    company.company = company.company || {};
    company.branch = company.branch || {};

    const urls = new Set();
    if (company.company.logo_url) urls.add(company.company.logo_url);
    if (company.branch.logo_url) urls.add(company.branch.logo_url);
    for (const section of Object.values(config.sections || {})) {
      for (const field of section.fields || []) {
        const registryEntry = registry?.fields?.[field.field];
        if (field.custom_value && (registryEntry?.field_type === "image" || /_logo$/.test(field.field))) {
          urls.add(field.custom_value);
        }
      }
    }

    // Fetch each distinct image once. A custom logo is embedded in the cached
    // configuration; otherwise the embedded company/branch logo is used by the
    // normal field data_source rule. The live/server configuration is untouched.
    const embedded = new Map(await Promise.all(
      [...urls].map(async url => [url, await urlToBase64(url)])
    ));
    if (company.company.logo_url) company.company.logo_url = embedded.get(company.company.logo_url);
    if (company.branch.logo_url) company.branch.logo_url = embedded.get(company.branch.logo_url);
    for (const section of Object.values(config.sections || {})) {
      for (const field of section.fields || []) {
        if (field.custom_value && embedded.has(field.custom_value)) {
          field.custom_value = embedded.get(field.custom_value);
        }
      }
    }
    return { configuration: config, companyData: company };
  }

  async function fetchStylesheet() {
    const response = await fetch("/static/invoice_designer/css/designer.css");
    if (!response.ok) throw new Error(`Could not cache print CSS (${response.status})`);
    return normalizeStylesheet(await response.text());
  }

  /**
   * Save one completely self-contained offline template. After this one write,
   * local printing needs a single template_configs read and no HTTP request.
   */
  async function saveTemplateForOffline({
    documentType, pageType, configuration, registry, companyData, cssText = "", updatedAt = null,
  }) {
    if (!window.IndexDBConfig?.save_update_record) {
      throw new Error("IndexedDB is not ready; the template cannot be saved for offline printing");
    }
    if (!registry?.fields) throw new Error("The field registry is not ready");
    if (!companyData) throw new Error("Company data is not ready; reload the designer before saving offline");

    const cssPromise = cssText
      ? Promise.resolve(normalizeStylesheet(cssText))
      : getCachedStylesheet().then(css => css || fetchStylesheet());
    const [assets, css] = await Promise.all([
      embedTemplateAssets(configuration, companyData, registry),
      cssPromise,
    ]);
    const record = {
      key: `${documentType}_${pageType}`,
      document_type: documentType,
      page_type: pageType,
      configuration: assets.configuration,
      registry: cloneJson(registry),
      company_data: assets.companyData,
      css,
      cache_version: 2,
      updated_at: updatedAt || new Date().toISOString(),
    };
    await window.IndexDBConfig.save_update_record("template_configs", record);
    return record;
  }

  // ── Public: preloadOfflineRenderData ─────────────────────────────────────

  async function preloadOfflineRenderData() {
    if (!window.IndexDBConfig) {
      console.warn("[OTE] IndexDBConfig not ready");
      return;
    }

    // Only shared assets are preloaded. Templates are cached when saved, which
    // avoids the old 24 sequential configuration requests on every new session.
    const jobs = [
      (async () => {
        const response = await fetch(window.FIELD_REGISTRY_API_URL || "/invoice-designer/api/field-registry/");
        if (!response.ok) throw new Error(`Registry preload failed (${response.status})`);
        const registry = await response.json();
        populateFormatAliases(registry);
        await idbSet("app_cache", { key: "field_registry", data: registry, updated_at: new Date().toISOString() });
      })(),
      (async () => {
        const response = await fetch("/invoice-designer/api/company-preview/");
        if (!response.ok) throw new Error(`Company preload failed (${response.status})`);
        const companyData = await response.json();
        const assets = await embedTemplateAssets({ sections: {} }, companyData, { fields: {} });
        await idbSet("app_cache", { key: "company_data", data: assets.companyData, updated_at: new Date().toISOString() });
      })(),
      (async () => {
        const css = await fetchStylesheet();
        await idbSet("app_cache", { key: "designer_css", data: css, updated_at: new Date().toISOString() });
      })(),
    ];
    const results = await Promise.allSettled(jobs);
    results.filter(result => result.status === "rejected").forEach(result => {
      console.warn("[OTE] Offline asset preload failed", result.reason);
    });
  }

  // ── Public cache readers ──────────────────────────────────────────────────

  async function getCachedRegistry() {
    const rec = await idbGet("app_cache", "field_registry");
    const registry = rec?.data || null;
    if (registry) populateFormatAliases(registry);
    return registry;
  }

  async function getCachedCompanyData() {
    const rec = await idbGet("app_cache", "company_data");
    return rec?.data || null;
  }

  async function getCachedStylesheet() {
    const rec = await idbGet("app_cache", "designer_css");
    return rec?.data ? normalizeStylesheet(rec.data) : "";
  }

  return {
    renderFromCache,
    preloadOfflineRenderData,
    saveTemplateForOffline,
    getCachedRegistry,
    getCachedCompanyData,
    getCachedStylesheet,
  };
})();