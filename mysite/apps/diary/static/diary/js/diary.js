import { GlobalSearchModal } from "/static/mysearch/js/global_search_modal.js";

const root = document.getElementById("diaryRoot");
const apiBase = root?.dataset.apiBase || "/diary/api/items/";
const todayValue = root?.dataset.today || new Date().toISOString().slice(0, 10);
const byId = (id) => document.getElementById(id);
let toastTimer = null;

const getCsrfToken = () => {
    const inputToken = document.querySelector(".diary-csrf-source [name=csrfmiddlewaretoken]")?.value;
    if (inputToken) return inputToken;
    const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
};

const canCreateKind = (kind) => {
    if (!root) return false;
    if (kind === "NOTE" || kind === "TASK") return root.dataset.canCreateNote === "true";
    if (kind === "PAYABLE") return root.dataset.canAddPayable === "true";
    if (kind === "RECEIVABLE") return root.dataset.canAddReceivable === "true";
    return false;
};

function showToast(message, isError = false) {
    const toast = byId("diaryToast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 3000);
}

function showFormError(id, message = "") {
    const element = byId(id);
    if (!element) return;
    element.textContent = message;
    element.hidden = !message;
}

function openOverlay(id) {
    const overlay = byId(id);
    if (!overlay) return;
    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    const firstInput = overlay.querySelector("input:not([type=hidden]), select, textarea, button");
    window.setTimeout(() => firstInput?.focus(), 20);
}

function closeOverlay(id) {
    const overlay = byId(id);
    if (!overlay) return;
    overlay.hidden = true;
    overlay.setAttribute("aria-hidden", "true");
    if (!["diaryItemOverlay", "diaryActionOverlay", "diaryHistoryOverlay"].some((overlayId) => {
        const element = byId(overlayId);
        return element && !element.hidden;
    })) {
        document.body.style.overflow = "";
    }
}

function setOptionIfMissing(select, value, label) {
    if (![...select.options].some((option) => option.value === value)) {
        select.add(new Option(label, value));
    }
}

function setEntryTypeFields() {
    const kind = byId("diaryItemKind")?.value;
    const isMoney = kind === "PAYABLE" || kind === "RECEIVABLE";
    const isNoteOrTask = kind === "NOTE" || kind === "TASK";
    document.querySelectorAll(".diary-account-fields").forEach((field) => { field.hidden = !isMoney; });
    document.querySelectorAll(".diary-money-fields").forEach((field) => { field.hidden = !isMoney; });
    document.querySelectorAll(".diary-repeat-field").forEach((field) => { field.hidden = !isMoney; });
    document.querySelectorAll(".diary-followup-field").forEach((field) => { field.hidden = !isMoney; });
    document.querySelectorAll(".diary-pinned-field").forEach((field) => { field.hidden = kind !== "NOTE"; });
    if (byId("diaryScheduledDateLabel")) {
        byId("diaryScheduledDateLabel").textContent = isMoney ? "Due date" : (kind === "TASK" ? "Schedule date" : "Note date");
    }
    if (byId("diaryAmount")) byId("diaryAmount").required = isMoney;
    if (byId("diaryAccountCode")) byId("diaryAccountCode").required = isMoney;
    if (byId("diaryFollowupDate") && !isNoteOrTask) byId("diaryFollowupDate").value = "";
}

function resetItemForm(kind = "") {
    const form = byId("diaryItemForm");
    form?.reset();
    byId("diaryItemId").value = "";
    byId("diaryItemKind").disabled = false;
    byId("diaryAccountCode").value = "";
    byId("diaryAccountName").value = "";
    byId("diaryScheduledDate").value = todayValue;
    showFormError("diaryItemError");
    const select = byId("diaryItemKind");
    if (kind) {
        setOptionIfMissing(select, kind, kind);
        select.value = kind;
    } else if (select.options.length) {
        select.selectedIndex = 0;
    }
    setEntryTypeFields();
}

function openCreate(kind = "") {
    if (kind && !canCreateKind(kind)) {
        showToast("You do not have permission to create this entry type.", true);
        return;
    }
    if (!kind && !["NOTE", "TASK", "PAYABLE", "RECEIVABLE"].some(canCreateKind)) {
        showToast("You do not have permission to create diary entries.", true);
        return;
    }
    resetItemForm(kind);
    byId("diaryItemModalTitle").textContent = "New entry";
    openOverlay("diaryItemOverlay");
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        ...options,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
            ...(options.headers || {}),
        },
    });
    let data;
    try {
        data = await response.json();
    } catch (_error) {
        data = { success: false, message: "The server returned an unexpected response." };
    }
    if (!response.ok || !data.success) {
        throw new Error(data.message || "The request could not be completed.");
    }
    return data;
}

async function openEdit(id) {
    if (root?.dataset.canUpdate !== "true") return;
    try {
        const result = await requestJson(`${apiBase}${id}/`, { headers: {} });
        const item = result.item;
        resetItemForm(item.kind);
        setOptionIfMissing(byId("diaryItemKind"), item.kind, item.kind_label);
        byId("diaryItemKind").value = item.kind;
        byId("diaryItemKind").disabled = true;
        byId("diaryItemId").value = item.id;
        byId("diaryItemTitle").value = item.title || "";
        byId("diaryItemDetails").value = item.details || "";
        byId("diaryScheduledDate").value = item.scheduled_date || todayValue;
        byId("diaryAccountCode").value = item.acc_code || "";
        byId("diaryAccountName").value = item.account_name ? `${item.account_name} (Code ${item.acc_code})` : (item.acc_code ? `Account ${item.acc_code}` : "");
        byId("diaryAmount").value = item.amount || "";
        byId("diaryFollowupDate").value = item.follow_up_date || "";
        byId("diaryRepeatDays").value = item.repeat_every_days || "";
        byId("diaryPinned").checked = Boolean(item.pinned);
        setEntryTypeFields();
        byId("diaryItemModalTitle").textContent = "Edit entry";
        openOverlay("diaryItemOverlay");
    } catch (error) {
        showToast(error.message, true);
    }
}

function itemPayload() {
    const kind = byId("diaryItemKind").value;
    const isMoney = kind === "PAYABLE" || kind === "RECEIVABLE";
    return {
        kind,
        title: byId("diaryItemTitle").value.trim(),
        details: byId("diaryItemDetails").value.trim(),
        scheduled_date: byId("diaryScheduledDate").value,
        acc_code: isMoney ? byId("diaryAccountCode").value : "",
        amount: isMoney ? byId("diaryAmount").value : "",
        follow_up_date: byId("diaryFollowupDate").value,
        repeat_every_days: isMoney ? byId("diaryRepeatDays").value : "",
        pinned: byId("diaryPinned").checked,
    };
}

async function saveItem(event) {
    event.preventDefault();
    showFormError("diaryItemError");
    const kind = byId("diaryItemKind").value;
    if (!kind) {
        showFormError("diaryItemError", "Choose an entry type you have permission to create.");
        return;
    }
    if ((kind === "PAYABLE" || kind === "RECEIVABLE") && !byId("diaryAccountCode").value) {
        showFormError("diaryItemError", "Search for and select an account.");
        return;
    }

    const id = byId("diaryItemId").value;
    const saveButton = byId("diaryItemSaveButton");
    saveButton.disabled = true;
    try {
        await requestJson(id ? `${apiBase}${id}/update/` : apiBase, {
            method: "POST",
            body: JSON.stringify(itemPayload()),
        });
        closeOverlay("diaryItemOverlay");
        showToast(id ? "Entry updated." : "Entry saved.");
        window.location.reload();
    } catch (error) {
        showFormError("diaryItemError", error.message);
    } finally {
        saveButton.disabled = false;
    }
}

function buildActionOptions(kind) {
    const select = byId("diaryActionType");
    select.replaceChildren();
    if (kind === "TASK") {
        select.add(new Option("Mark task complete", "done"));
        return;
    }
    const receive = kind === "RECEIVABLE";
    select.add(new Option(receive ? "Full received" : "Full paid", "full"));
    select.add(new Option(receive ? "Partial received" : "Partial paid", "partial"));
    select.add(new Option(receive ? "Not received — extend date" : "Not paid — extend date", "extend"));
    select.add(new Option("Settle / adjust without cash", "settle"));
}

function syncActionFields() {
    const action = byId("diaryActionType").value;
    const showAmount = action === "partial" || action === "settle";
    const showDate = action === "partial" || action === "settle" || action === "extend";
    const amountField = document.querySelector(".diary-action-amount-field");
    const dateField = document.querySelector(".diary-action-date-field");
    const reasonField = document.querySelector(".diary-settlement-reason-field");
    if (amountField) amountField.hidden = !showAmount;
    if (dateField) dateField.hidden = !showDate;
    if (reasonField) reasonField.hidden = action !== "settle";
    byId("diaryActionAmount").required = action === "partial";
    byId("diaryActionNextDate").required = action === "extend";
    byId("diarySettlementReason").required = action === "settle";
    byId("diaryActionModalTitle").textContent = action === "done" ? "Complete task" : "Record reminder action";
    byId("diaryActionSaveButton").textContent = action === "done" ? "Complete task" : "Save action";
}

async function openAction(id, kind = "") {
    if (root?.dataset.canUpdate !== "true") return;
    try {
        const result = await requestJson(`${apiBase}${id}/`, { headers: {} });
        const item = result.item;
        const actualKind = kind || item.kind;
        byId("diaryActionItemId").value = String(item.id);
        byId("diaryActionKind").value = actualKind;
        byId("diaryActionAmount").value = "";
        byId("diaryActionNextDate").value = "";
        byId("diaryActionNote").value = "";
        byId("diarySettlementReason").value = "";
        showFormError("diaryActionError");
        if (actualKind === "PAYABLE" || actualKind === "RECEIVABLE") {
            byId("diaryActionBalance").textContent = `Account: ${item.account_name || `Account ${item.acc_code}`} · Remaining: Rs ${item.remaining_amount}`;
        } else {
            byId("diaryActionBalance").textContent = item.title || "Task";
        }
        buildActionOptions(actualKind);
        syncActionFields();
        openOverlay("diaryActionOverlay");
    } catch (error) {
        showToast(error.message, true);
    }
}

async function saveAction(event) {
    event.preventDefault();
    showFormError("diaryActionError");
    const action = byId("diaryActionType").value;
    const payload = {
        action,
        amount: byId("diaryActionAmount").value,
        next_date: byId("diaryActionNextDate").value,
        reason: byId("diarySettlementReason").value,
        note: byId("diaryActionNote").value.trim(),
    };
    const id = byId("diaryActionItemId").value;
    const button = byId("diaryActionSaveButton");
    button.disabled = true;
    try {
        await requestJson(`${apiBase}${id}/action/`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        closeOverlay("diaryActionOverlay");
        showToast("Action saved.");
        window.location.reload();
    } catch (error) {
        showFormError("diaryActionError", error.message);
    } finally {
        button.disabled = false;
    }
}

async function openHistory(id) {
    const content = byId("diaryHistoryContent");
    content.innerHTML = '<p class="diary-muted">Loading history…</p>';
    openOverlay("diaryHistoryOverlay");
    try {
        const result = await requestJson(`${apiBase}${id}/history/`, { headers: {} });
        content.replaceChildren();
        if (!result.history.length) {
            const empty = document.createElement("p");
            empty.className = "diary-muted";
            empty.textContent = "No history is recorded for this entry.";
            content.appendChild(empty);
            return;
        }
        const list = document.createElement("div");
        list.className = "diary-history-list";
        result.history.forEach((entry) => {
            const row = document.createElement("article");
            row.className = "diary-history-row";
            const action = document.createElement("div");
            action.className = "diary-history-action";
            action.textContent = entry.action;
            const description = document.createElement("div");
            description.className = "diary-history-description";
            const metaParts = [];
            if (entry.amount) metaParts.push(`Rs ${entry.amount}`);
            if (entry.reason) metaParts.push(entry.reason);
            if (entry.old_due_date || entry.new_due_date) {
                metaParts.push(`${entry.old_due_date || "—"} → ${entry.new_due_date || "—"}`);
            }
            if (entry.old_amount || entry.new_amount) {
                metaParts.push(`Amount ${entry.old_amount || "—"} → ${entry.new_amount || "—"}`);
            }
            if (entry.balance_after) metaParts.push(`Balance Rs ${entry.balance_after}`);
            if (metaParts.length) {
                const meta = document.createElement("div");
                meta.className = "diary-history-note";
                meta.textContent = metaParts.join(" · ");
                description.appendChild(meta);
            }
            if (entry.note) {
                const note = document.createElement("div");
                note.className = "diary-history-note";
                note.textContent = entry.note;
                description.appendChild(note);
            }
            const time = document.createElement("time");
            time.className = "diary-history-time";
            time.textContent = entry.created_at;
            row.append(action, description, time);
            list.appendChild(row);
        });
        content.appendChild(list);
    } catch (error) {
        content.replaceChildren();
        const message = document.createElement("p");
        message.className = "diary-form-error";
        message.textContent = error.message;
        content.appendChild(message);
    }
}

async function deleteItem(id) {
    if (root?.dataset.canDelete !== "true") return;
    if (!window.confirm("Delete this diary entry? Its history will be kept.")) return;
    try {
        await requestJson(`${apiBase}${id}/delete/`, {
            method: "POST",
            body: JSON.stringify({ note: "Deleted from the diary view." }),
        });
        showToast("Entry deleted.");
        window.location.reload();
    } catch (error) {
        showToast(error.message, true);
    }
}

const DiaryUI = {
    openCreate,
    openEdit,
    openAction,
    openHistory,
};
window.DiaryUI = DiaryUI;

byId("diaryNewEntryButton")?.addEventListener("click", () => openCreate());
byId("diaryItemKind")?.addEventListener("change", setEntryTypeFields);
byId("diaryItemForm")?.addEventListener("submit", saveItem);
byId("diaryActionType")?.addEventListener("change", syncActionFields);
byId("diaryActionForm")?.addEventListener("submit", saveAction);

document.addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-diary-edit]");
    const actionButton = event.target.closest("[data-diary-action]");
    const historyButton = event.target.closest("[data-diary-history]");
    const deleteButton = event.target.closest("[data-diary-delete]");
    const closeButton = event.target.closest("[data-diary-close]");

    if (editButton) openEdit(editButton.dataset.diaryEdit);
    if (actionButton) openAction(actionButton.dataset.diaryAction, actionButton.dataset.kind);
    if (historyButton) openHistory(historyButton.dataset.diaryHistory);
    if (deleteButton) deleteItem(deleteButton.dataset.diaryDelete);
    if (closeButton) closeOverlay(closeButton.dataset.diaryClose);
    if (event.target.classList.contains("diary-modal-overlay")) closeOverlay(event.target.id);
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const globalSearch = byId("gsm-overlay");
    if (globalSearch && globalSearch.getAttribute("aria-hidden") === "false") return;
    const topOverlay = ["diaryHistoryOverlay", "diaryActionOverlay", "diaryItemOverlay"]
        .map(byId)
        .find((overlay) => overlay && !overlay.hidden);
    if (topOverlay) closeOverlay(topOverlay.id);
});

GlobalSearchModal.init([
    {
        modalId: "diaryAccountSearch",
        triggerSelector: "#diaryAccountSearchButton",
        title: "Find account",
        placeholder: "Search by account name or code...",
        appLabel: "myaccounts",
        modelName: "Accounts",
        primaryKey: "ACC_CODE",
        indexdbStore: null,
        searchFields: ["ACC_CODE", "ACC_NAME"],
        excludeFilters: { TYPE__exact: "Group" },
        displayColumns: [
            { key: "ACC_CODE", header: "Code", width: "100px" },
            { key: "ACC_NAME", header: "Account name" },
        ],
        pageSize: 25,
        onSelect(item) {
            byId("diaryAccountCode").value = item.ACC_CODE;
            byId("diaryAccountName").value = `${item.ACC_NAME || "Account"} (Code ${item.ACC_CODE})`;
        },
    },
]);
