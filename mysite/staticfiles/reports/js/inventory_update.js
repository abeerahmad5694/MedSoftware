(() => {
  "use strict";
  const $ = (id) => document.getElementById("iu-" + id);
  const root = document.getElementById("inventory-editor");
  const config = JSON.parse($("config").textContent),
    fields = config.fields,
    engine = window.InventoryFormulas;
  const originals = new Map(),
    drafts = new Map(),
    selected = new Set();
  let rows = [],
    page = 1,
    count = 0,
    rules = [],
    undo = [],
    busy = false,
    loadSequence = 0;
  let currentFilters = { manufacturer: "", category: "", q: "" };
  const numeric = fields.filter((f) => f.type === "number");
  const derivedFields = [
    {
      name: "discounted_base_price",
      label: "Retail after discount",
      type: "derived",
    },
    {
      name: "discounted_ws_price",
      label: "Wholesale after discount",
      type: "derived",
    },
  ];
  function node(tag, text, cls) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  }
  function option(select, value, text) {
    const el = node("option", text);
    el.value = value;
    select.append(el);
  }
  function message(text = "", error = false) {
    $("message").textContent = text;
    $("message").classList.toggle("iu-error", error);
  }
  function rowData(id) {
    return drafts.get(id) || originals.get(id);
  }
  function normalized(value, field) {
    if (value === null || value === undefined || value === "") return "";
    if (field.type === "number" || field.type === "select")
      return String(Number(value));
    return String(value);
  }
  function changes(id, row = rowData(id)) {
    const original = originals.get(id),
      result = {};
    for (const field of fields)
      if (
        normalized(row[field.name], field) !==
        normalized(original[field.name], field)
      )
        result[field.name] = row[field.name];
    return result;
  }
  function put(id, row) {
    if (Object.keys(changes(id, row)).length) drafts.set(id, row);
    else drafts.delete(id);
  }
  function remember() {
    undo.push(new Map([...drafts].map(([id, row]) => [id, { ...row }])));
    if (undo.length > 30) undo.shift();
  }
  function status() {
    $("dirty").textContent = drafts.size;
    $("review").disabled = busy || !drafts.size;
    $("discard").disabled = busy || !drafts.size;
    $("undo").disabled = busy || !undo.length;
    $("prev").disabled = busy || page <= 1;
    $("next").disabled = busy || page * 100 >= count;
    $("page").textContent =
      `Page ${page} of ${Math.max(1, Math.ceil(count / 100))} · ${count} matching items`;
  }
  function visibleRows() {
    const query = $("local-search").value.trim().toLocaleLowerCase();
    return rows.filter((id) => {
      const row = rowData(id);
      return (
        !query ||
        [
          "prod_name",
          "alias_name",
          "barcode",
          "manualbc",
          "barcode2",
          "id",
        ].some((k) =>
          String(row[k] || "")
            .toLocaleLowerCase()
            .includes(query),
        )
      );
    });
  }
  function columns() {
    const group = $("group").value;
    const chosen = fields.filter(
      (f) =>
        group === "All" ||
        (group === "Prices"
          ? ["Retail", "Wholesale"].includes(f.group)
          : f.group === group),
    );
    for (const derived of derivedFields) {
      const position = chosen.findIndex(
        (f) =>
          f.name ===
          (derived.name === "discounted_base_price"
            ? "base_disc_per"
            : "ws_disc_per"),
      );
      if (position >= 0) chosen.splice(position + 1, 0, derived);
    }
    return chosen;
  }
  function labelValue(field, value) {
    if (value === null || value === undefined || value === "") return "(blank)";
    return field.type === "select"
      ? field.options.find((o) => String(o.id) === String(value))?.name ||
          String(value)
      : String(value);
  }
  function control(field, value) {
    let el;
    if (field.type === "select" || field.type === "boolean") {
      el = node("select");
      option(el, "", "—");
      if (field.type === "boolean") {
        option(el, "true", "Active");
        option(el, "false", "Inactive");
      } else for (const o of field.options) option(el, o.id, o.name);
    } else {
      el = node("input");
      el.type = field.type;
      if (field.type === "number") {
        el.step = field.step;
        el.min = ["carton_qty", "dzn_qty"].includes(field.name) ? "1" : "0";
        if (field.name.endsWith("_disc_per")) el.max = "100";
      }
      if (field.type === "text")
        el.maxLength = field.name === "prod_name_ur" ? 500 : 255;
    }
    if (field.name === "prod_name_ur") {
      el.dir = "rtl";
      el.lang = "ur";
    }
    el.value = value ?? "";
    el.required = field.required;
    return el;
  }
  function render() {
    const cols = columns(),
      visible = visibleRows(),
      head = $("table").querySelector("thead"),
      body = $("table").querySelector("tbody");
    head.replaceChildren();
    body.replaceChildren();
    const header = node("tr"),
      th = node("th"),
      all = node("input");
    all.type = "checkbox";
    all.setAttribute("aria-label", "Select visible items");
    all.checked = !!visible.length && visible.every((id) => selected.has(id));
    all.indeterminate = visible.some((id) => selected.has(id)) && !all.checked;
    all.addEventListener("change", () => {
      visible.forEach((id) =>
        all.checked ? selected.add(id) : selected.delete(id),
      );
      render();
    });
    th.append(all);
    header.append(th, node("th", "Item / company / category"));
    for (const field of cols) header.append(node("th", field.label));
    head.append(header);
    for (const id of visible) {
      const row = rowData(id),
        tr = node("tr");
      tr.dataset.id = id;
      const selectCell = node("td"),
        check = node("input");
      check.type = "checkbox";
      check.checked = selected.has(id);
      check.setAttribute("aria-label", "Select " + row.prod_name);
      check.addEventListener("change", () => {
        check.checked ? selected.add(id) : selected.delete(id);
      });
      selectCell.append(check);
      tr.append(selectCell);
      const identity = node("td");
      identity.append(node("span", row.prod_name, "iu-item-name"));
      const manufacturer = labelValue(
        fields.find((f) => f.name === "manufacturer"),
        row.manufacturer,
      );
      const category = labelValue(
        fields.find((f) => f.name === "category"),
        row.category,
      );
      identity.append(
        node("span", `#${id} · ${manufacturer} · ${category}`, "iu-item-meta"),
      );
      identity.append(
        node(
          "span",
          `On hand: ${row.bal_qty ?? 0} · Updated by: ${row.updated_by || "—"}`,
          "iu-item-meta",
        ),
      );
      tr.append(identity);
      for (const field of cols) {
        const td = node("td");
        td.dataset.label = field.label;
        td.dataset.field = field.name;
        if (field.type === "derived") {
          const output = node("output");
          output.dataset.derived = field.name;
          td.append(output);
        } else {
          const input = control(field, row[field.name]);
          input.dataset.field = field.name;
          input.setAttribute("aria-label", `${row.prod_name}: ${field.label}`);
          input.autocomplete = "off";
          input.addEventListener("change", () => edit(id, field, input, tr));
          input.addEventListener("keydown", (event) => {
            if (event.key !== "Enter") return;
            event.preventDefault();
            if (!edit(id, field, input, tr)) return;
            const ids = visibleRows(),
              next = ids[ids.indexOf(id) + (event.shiftKey ? -1 : 1)];
            if (next !== undefined) {
              const target = body.querySelector(
                `tr[data-id="${next}"] [data-field="${field.name}"] input, tr[data-id="${next}"] [data-field="${field.name}"] select`,
              );
              target?.focus();
              if (target?.select && target.type !== "date") target.select();
            }
          });
          td.append(input);
        }
        tr.append(td);
      }
      body.append(tr);
      refreshRow(tr, id);
    }
    $("empty").hidden = visible.length !== 0;
    $("count").textContent =
      `${visible.length} visible / ${rows.length} loaded`;
    status();
  }
  function refreshRow(tr, id) {
    const row = rowData(id),
      changed = changes(id);
    for (const td of tr.querySelectorAll("td[data-field]")) {
      td.classList.toggle("iu-changed", td.dataset.field in changed);
      const input = td.querySelector("input,select");
      if (input) input.value = row[td.dataset.field] ?? "";
      const output = td.querySelector("output");
      if (output) {
        try {
          output.textContent = engine
            .number(row, output.dataset.derived)
            .toFixed(2);
        } catch {
          output.textContent = "Invalid";
        }
      }
    }
  }
  function readValue(input, field) {
    if (!input.checkValidity()) {
      input.reportValidity();
      throw Error("Check the highlighted value.");
    }
    return input.value === ""
      ? null
      : field.type === "boolean"
        ? input.value === "true"
        : input.value;
  }
  function edit(id, field, input, tr) {
    if (busy) return false;
    try {
      const value = readValue(input, field);
      if (
        normalized(value, field) === normalized(rowData(id)[field.name], field)
      )
        return true;
      let row = { ...rowData(id), [field.name]: value };
      if ($("auto").checked && field.type === "number")
        row = engine.run(
          row,
          engine.compile(rules, fields),
          fields,
          field.name,
        );
      if (!drafts.has(id) && drafts.size >= 500)
        throw Error("Save your 500 drafts before editing more items.");
      remember();
      put(id, row);
      refreshRow(tr, id);
      status();
      message();
      return true;
    } catch (error) {
      message(error.message, true);
      input.value = rowData(id)[field.name] ?? "";
      return false;
    }
  }
  async function load(nextPage = 1) {
    const sequence = ++loadSequence;
    busy = true;
    status();
    message("Loading inventory…");
    try {
      const url = new URL(root.dataset.url, location.href);
      for (const [key, value] of Object.entries({
        ...currentFilters,
        data: "1",
        page: nextPage,
      }))
        url.searchParams.set(key, value);
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
      });
      if (
        !response.ok ||
        !response.headers.get("content-type")?.includes("application/json")
      )
        throw Error(
          "Could not load inventory. Check your connection and permissions, or sign in again.",
        );
      const data = await response.json();
      if (sequence !== loadSequence) return;
      page = data.page;
      count = data.count;
      rows = data.rows.map((r) => r.id);
      selected.clear();
      for (const row of data.rows)
        if (!drafts.has(row.id)) originals.set(row.id, row);
      // Old undo snapshots must not restore drafts against newly loaded baselines.
      undo = [];
      message();
    } catch (error) {
      if (sequence === loadSequence) message(error.message, true);
    } finally {
      if (sequence === loadSequence) {
        busy = false;
        render();
      }
    }
  }
  function scopeIds() {
    const visible = visibleRows();
    return $("scope").value === "visible"
      ? visible
      : visible.filter((id) => selected.has(id));
  }
  function bulk(transform) {
    if (busy) return;
    try {
      const ids = scopeIds();
      if (!ids.length)
        throw Error(
          "Select items, or choose all visible items as the action scope.",
        );
      if (
        !confirm(
          `Preview changes for ${ids.length} items on this page? Nothing is saved yet.`,
        )
      )
        return;
      const pending = ids.map((id) => {
        try {
          return [id, transform({ ...rowData(id) })];
        } catch (error) {
          throw Error(`#${id}: ${error.message} No bulk changes applied.`);
        }
      });
      const newIds = new Set(drafts.keys());
      pending.forEach(([id, row]) => {
        if (Object.keys(changes(id, row)).length) newIds.add(id);
      });
      if (newIds.size > 500)
        throw Error("Save your existing drafts first (500-item limit).");
      remember();
      pending.forEach(([id, row]) => put(id, row));
      render();
      message(
        `Previewed changes for ${ids.length} items. Review & save to commit.`,
      );
    } catch (error) {
      message(error.message, true);
    }
  }
  function showRules() {
    $("rules").replaceChildren();
    if (!rules.length)
      $("rules").append(
        node("li", "No rules yet. Start with a preset or add your own."),
      );
    rules.forEach((rule, index) => {
      const li = node("li"),
        code = node("code", `${rule.target} = ${rule.expression}`),
        remove = node("button", "Remove");
      remove.type = "button";
      remove.addEventListener("click", () => {
        rules.splice(index, 1);
        showRules();
      });
      li.append(code, remove);
      $("rules").append(li);
    });
  }
  function db() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open("erp-inventory-update-formulas", 1);
      request.onupgradeneeded = () =>
        request.result.createObjectStore("preferences");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(Error("Browser database blocked."));
    });
  }
  async function preferences(save = false) {
    let database;
    try {
      if (save) engine.compile(rules, fields);
      database = await db();
      const value = await new Promise((resolve, reject) => {
        const tx = database.transaction(
            "preferences",
            save ? "readwrite" : "readonly",
          ),
          store = tx.objectStore("preferences");
        const request = save
          ? store.put({ rules, auto: $("auto").checked }, config.storageKey)
          : store.get(config.storageKey);
        tx.oncomplete = () => resolve(request.result);
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
      if (save)
        message(
          "Formula rules saved in this browser for your user, company and branch.",
        );
      else if (value) {
        engine.compile(value.rules, fields);
        rules = value.rules;
        $("auto").checked = value.auto === true;
        showRules();
      }
    } catch (error) {
      message(
        "Formula storage unavailable or invalid. You can still edit and save inventory. " +
          error.message,
        true,
      );
    } finally {
      database?.close();
    }
  }
  function updateBulkControl() {
    const field = fields.find((f) => f.name === $("bulk-field").value),
      old = $("bulk-value");
    const input = control(field, null);
    input.id = "iu-bulk-value";
    old.replaceWith(input);
    const numericField = field.type === "number";
    $("operation").disabled = !numericField;
    if (!numericField) $("operation").value = "set";
    if (numericField && $("operation").value !== "set") {
      input.removeAttribute("min");
      input.removeAttribute("max");
      input.step = "any";
    }
  }
  function review() {
    if (!drafts.size || busy) return;
    $("review-list").replaceChildren();
    let cells = 0;
    for (const [id, row] of drafts) {
      const section = node("section");
      section.append(node("strong", `#${id} · ${row.prod_name}`));
      const ul = node("ul");
      for (const [key, value] of Object.entries(changes(id))) {
        const field = fields.find((f) => f.name === key);
        cells++;
        ul.append(
          node(
            "li",
            `${field.label}: ${labelValue(field, originals.get(id)[key])} → ${labelValue(field, value)}`,
          ),
        );
      }
      section.append(ul);
      $("review-list").append(section);
    }
    $("review-summary").textContent =
      `${drafts.size} items · ${cells} changed fields · all pages`;
    $("review-dialog").showModal();
  }
  async function save() {
    if (busy || !drafts.size) return;
    busy = true;
    status();
    $("save").disabled = true;
    $("cancel-save").disabled = true;
    try {
      const payload = {
        changes: [...drafts.keys()].map((id) => ({
          id,
          version: originals.get(id).version,
          values: changes(id),
        })),
      };
      const response = await fetch(root.dataset.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": root.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: JSON.stringify(payload),
      });
      if (!response.headers.get("content-type")?.includes("application/json"))
        throw Error(
          "Unexpected server response. Drafts retained; check your login and reload before retrying if the save outcome is uncertain.",
        );
      const data = await response.json();
      if (!response.ok) {
        const errors = Object.entries(data.errors || {}).flatMap(
          ([id, values]) =>
            Object.entries(values).map(
              ([field, errors]) =>
                `#${id} ${field}: ${errors.map((e) => e.message).join(" ")}`,
            ),
        );
        throw Error(
          [
            data.error || "Save failed.",
            data.conflicts?.length
              ? "Conflicting IDs: " + data.conflicts.join(", ")
              : "",
            ...errors,
          ]
            .filter(Boolean)
            .join("\n"),
        );
      }
      for (const row of data.rows) {
        originals.set(row.id, row);
        drafts.delete(row.id);
      }
      undo = [];
      message(
        `Saved ${data.rows.length} items. Refresh offline inventory on other open POS/search screens before using the new prices.`,
      );
    } catch (error) {
      message(error.message, true);
    } finally {
      busy = false;
      $("save").disabled = false;
      $("cancel-save").disabled = false;
      $("review-dialog").close();
      render();
    }
  }
  for (const name of ["manufacturer", "category"])
    for (const o of fields.find((f) => f.name === name).options)
      option($(name === "manufacturer" ? "company" : "category"), o.id, o.name);
  for (const f of numeric) option($("target"), f.name, f.label);
  option($("insert"), "", "Choose a field…");
  for (const f of [...numeric, ...derivedFields])
    option($("insert"), f.name, f.label + " (" + f.name + ")");
  for (const f of fields) option($("bulk-field"), f.name, f.label);
  $("target").value = "carton_price";
  updateBulkControl();
  showRules();
  $("filters").addEventListener("submit", (event) => {
    event.preventDefault();
    if (busy) return;
    currentFilters = {
      manufacturer: $("company").value,
      category: $("category").value,
      q: $("query").value,
    };
    load();
  });
  $("prev").onclick = () => load(page - 1);
  $("next").onclick = () => load(page + 1);
  $("group").onchange = render;
  $("local-search").oninput = render;
  $("undo").onclick = () => {
    if (busy || !undo.length) return;
    const snapshot = undo.pop();
    drafts.clear();
    snapshot.forEach((row, id) => drafts.set(id, row));
    render();
    message("Last edit undone.");
  };
  $("discard").onclick = () => {
    if (
      !busy &&
      confirm(
        "Discard ALL unsaved drafts on every page and reload current values?",
      )
    ) {
      drafts.clear();
      undo = [];
      load(page);
    }
  };
  $("insert").onchange = () => {
    $("expression").value +=
      ($("expression").value ? " " : "") + $("insert").value;
    $("insert").value = "";
    $("expression").focus();
  };
  $("add-rule").onclick = () => {
    try {
      const rule = {
          target: $("target").value,
          expression: $("expression").value.trim(),
        },
        next = [...rules.filter((r) => r.target !== rule.target), rule];
      engine.compile(next, fields);
      rules = next;
      showRules();
      message("Rule added. Save rules to keep it for next time.");
    } catch (error) {
      message(error.message, true);
    }
  };
  $("use-preset").onclick = () => {
    if (!$("preset").value) return;
    const base =
      $("preset").value === "retail"
        ? "discounted_base_price"
        : "discounted_ws_price";
    const next = [
      ...rules.filter((r) => !["carton_price", "dzn_price"].includes(r.target)),
      { target: "carton_price", expression: `${base} * carton_qty` },
      { target: "dzn_price", expression: `${base} * dzn_qty` },
    ];
    try {
      engine.compile(next, fields);
      rules = next;
      showRules();
      message(
        "Preset ready. Pack quantities must be populated; blank quantities count as zero. Check pack discounts before applying.",
      );
    } catch (error) {
      message(error.message, true);
    }
  };
  $("store-rules").onclick = () => preferences(true);
  $("apply-rules").onclick = () => {
    try {
      if (!rules.length) throw Error("Add a formula first.");
      const compiled = engine.compile(rules, fields);
      bulk((row) => engine.run(row, compiled, fields));
    } catch (error) {
      message(error.message, true);
    }
  };
  $("bulk-field").onchange = updateBulkControl;
  $("operation").onchange = updateBulkControl;
  $("bulk-apply").onclick = () => {
    try {
      const field = fields.find((f) => f.name === $("bulk-field").value),
        operation = $("operation").value;
      const value = readValue($("bulk-value"), field);
      if (operation !== "set" && value === null)
        throw Error("Enter an amount or percentage.");
      bulk((row) => {
        if (operation === "set") row[field.name] = value;
        else {
          const before = Number(row[field.name] || 0),
            amount = Number(value),
            result =
              operation === "add"
                ? before + amount
                : before * (1 + amount / 100);
          row[field.name] =
            field.step === "1" ? String(Math.round(result)) : result.toFixed(2);
        }
        // Reuse the native constraints for calculated and set values.
        const check = control(field, row[field.name]);
        if (!check.checkValidity()) throw Error(`Invalid ${field.label}.`);
        return $("auto").checked && field.type === "number"
          ? engine.run(row, engine.compile(rules, fields), fields, field.name)
          : row;
      });
    } catch (error) {
      message(error.message, true);
    }
  };
  $("review").onclick = review;
  $("cancel-save").onclick = () => $("review-dialog").close();
  $("save").onclick = save;
  $("review-dialog").addEventListener("cancel", (event) => {
    if (busy) event.preventDefault();
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      document.activeElement?.blur();
      if (!$("review-dialog").open) review();
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (drafts.size) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  // Narrow draft-only bridge: the independent assistant cannot save inventory
  // or touch pricing/formulas. Snapshot checks protect edits made while awaiting
  // the external provider, even if the user has since navigated to another page.
  window.InventoryEditorUrdu = Object.freeze({
    snapshot() {
      if (busy) throw Error("Wait for the inventory operation to finish.");
      return scopeIds().map((id) => {
        const row = rowData(id);
        return {
          id,
          source: row.prod_name,
          originalUrdu: row.prod_name_ur || "",
          version: row.version,
        };
      });
    },
    apply(suggestions) {
      if (busy) throw Error("Wait for the inventory operation to finish.");
      const pending = [],
        ids = new Set();
      let skipped = 0;
      for (const suggestion of suggestions) {
        const row = rowData(suggestion.id);
        if (
          !row ||
          ids.has(suggestion.id) ||
          row.prod_name !== suggestion.source ||
          (row.prod_name_ur || "") !== suggestion.originalUrdu ||
          row.version !== suggestion.version
        ) {
          skipped++;
          continue;
        }
        const text = suggestion.text.trim();
        if (!text || text.length > 500)
          throw Error("Urdu suggestions must be between 1 and 500 characters.");
        ids.add(suggestion.id);
        pending.push([suggestion.id, { ...row, prod_name_ur: text }]);
      }
      const dirtyIds = new Set(drafts.keys());
      pending.forEach(([id, row]) => {
        if (Object.keys(changes(id, row)).length) dirtyIds.add(id);
      });
      if (dirtyIds.size > 500)
        throw Error("Save your existing drafts first (500-item limit).");
      if (pending.length) {
        remember();
        pending.forEach(([id, row]) => put(id, row));
        $("group").value = "Details";
        render();
      }
      return { applied: pending.length, skipped };
    },
  });
  load().then(() => preferences());
})();