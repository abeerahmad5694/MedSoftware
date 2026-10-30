
import { Helpers } from "/static/myaccounts/js/services/account_utils.js";
import { openAccountModal } from "/static/myaccounts/js/modals/global_account_form_modal.js";


const ICONS = {
    assets: `<svg viewBox="0 0 20 20" fill="none" stroke="#185FA5" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><rect x="2" y="5" width="16" height="12" rx="2"/><path d="M6 5V4a2 2 0 014 0v1"/><path d="M10 11v2"/></svg>`,
    liabilities: `<svg viewBox="0 0 20 20" fill="none" stroke="#3B6D11" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><path d="M10 3l7 4v6l-7 4-7-4V7z"/></svg>`,
    equity: `<svg viewBox="0 0 20 20" fill="none" stroke="#854F0B" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><circle cx="10" cy="10" r="7"/><path d="M10 7v6M7 10h6"/></svg>`,
    revenue: `<svg viewBox="0 0 20 20" fill="none" stroke="#185FA5" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><polyline points="3 13 7 9 11 12 17 6"/><polyline points="14 6 17 6 17 9"/></svg>`,
    expense: `<svg viewBox="0 0 20 20" fill="none" stroke="#993C1D" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><circle cx="10" cy="10" r="7"/><path d="M13 7l-6 6M7 7l6 6"/></svg>`,
    group: `<svg viewBox="0 0 20 20" fill="none" stroke="#5F5E5A" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><path d="M2 6h5l2-3h2l2 3h5"/><rect x="2" y="6" width="16" height="9" rx="1.5"/></svg>`,
    detail: `<svg viewBox="0 0 20 20" fill="none" stroke="#444441" stroke-width="1.6" stroke-linecap="round" width="16" height="16"><rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M7 8h6M7 12h4"/></svg>`,
};

const GetGroupTreeUrl = '/myaccounts/api/get-group-tree/'
const GetNextAccountCodeUrl = '/myaccounts/api/get-next-account-code/'
const GetDetailAccountsUrl = '/myaccounts/api/get-detail-accounts/'
const DETAIL_LEVEL = 4;

function chev(leaf) {
    return `<svg class="chevron${leaf ? ' leaf' : ''}" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="16" height="16" aria-hidden="true"><polyline points="5 3 11 8 5 13"/></svg>`;
}

function addBtn(html) {
    return `<button class="add-btn" aria-label="Add child account">${html}</button>`;
}

const plusSvg = `<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14" aria-hidden="true"><line x1="7" y1="2" x2="7" y2="12"/><line x1="2" y1="7" x2="12" y2="7"/></svg>`;

// Helper: build tree from flat list of groups
function buildTree(flatGroups) {
    const map = {};
    const roots = [];
    flatGroups.forEach(g => {
        g.children = [];
        g.icon = getIcon(g);
        map[g.code] = g;
    });

    flatGroups.forEach(g => {
        if (g.level === 1) {
            roots.push(g);
        } else {
            // Find parent
            let parentCode = g.code.substring(0, g.level - 1);
            if (map[parentCode]) {
                map[parentCode].children.push(g);
            } else {
                roots.push(g); // fallback
            }
        }
    });
    return roots;
}

function getIcon(node) {
    if (node.level === 1) {
        if (node.name.toLowerCase().includes('asset')) return 'assets';
        if (node.name.toLowerCase().includes('liabilit')) return 'liabilities';
        if (node.name.toLowerCase().includes('equit') || node.name.toLowerCase().includes('capital')) return 'equity';
        if (node.name.toLowerCase().includes('revenu') || node.name.toLowerCase().includes('sale') || node.name.toLowerCase().includes('income')) return 'revenue';
        if (node.name.toLowerCase().includes('expens') || node.name.toLowerCase().includes('cost')) return 'expense';
    }
    return 'group';
}

function buildNode(node) {
    const isLeaf = false; // groups only in tree
    const hasChildren = node.children && node.children.length > 0;
    const metaText = `Level ${node.level} group`;

    let childrenHtml = '';
    if (hasChildren) {
        const inner = node.children.map(c => buildNode(c)).join('');
        childrenHtml = `<div class="node-children"><div class="divider"></div><div class="children-inner">${inner}</div></div>`;
    }

    const showAdd = node.level < DETAIL_LEVEL;

    return `
  <div class="node-card collapsed" data-id="${node.code}" data-level="${node.level}" data-type="${node.type}" data-name="${node.name}" data-code="${node.code}" data-class="${node.class_field}">
    <div class="node-header" role="button" tabindex="0" aria-expanded="false">
      ${chev(!hasChildren)}
      <div class="node-icon">${ICONS[node.icon] || ICONS.group}</div>
      <div class="node-label">
        <div class="node-name">${node.name}</div>
        <div class="node-meta">${metaText}</div>
      </div>
      <span class="node-code">${node.code}</span>
      <span class="node-badge badge-group">group</span>
      ${showAdd ? addBtn(plusSvg) : ''}
    </div>
    ${childrenHtml}
  </div>`;
}

const root = document.getElementById('tree-root');

async function loadTree() {
    // Collect currently open nodes and active node
    const openNodes = Array.from(document.querySelectorAll('.node-card:not(.collapsed)')).map(n => n.dataset.code);
    const activeNode = document.querySelector('.node-card.active')?.dataset?.code;

    try {
        const res = await fetch(GetGroupTreeUrl);
        const json = await res.json();
        if (json.success) {
            const tree = buildTree(json.data);
            root.innerHTML = tree.map(n => buildNode(n)).join('');

            // Restore open nodes
            openNodes.forEach(code => {
                const node = document.querySelector(`.node-card[data-code="${code}"]`);
                if (node) {
                    node.classList.remove('collapsed');
                    const header = node.querySelector('.node-header');
                    if (header) header.setAttribute('aria-expanded', 'true');
                    const chv = node.querySelector('.chevron:not(.leaf)');
                    if (chv) chv.classList.add('open');
                }
            });

            // Restore active node
            if (activeNode) {
                const node = document.querySelector(`.node-card[data-code="${activeNode}"]`);
                if (node) node.classList.add('active');
            }

            // Auto-open parent of newly added node
            if (window.addingToParentCode) {
                const node = document.querySelector(`.node-card[data-code="${window.addingToParentCode}"]`);
                if (node) {
                    let curr = node;
                    while (curr && curr.classList.contains('node-card')) {
                        curr.classList.remove('collapsed');
                        const h = curr.querySelector('.node-header');
                        if (h) h.setAttribute('aria-expanded', 'true');
                        const c = curr.querySelector('.chevron:not(.leaf)');
                        if (c) c.classList.add('open');
                        curr = curr.parentElement?.closest('.node-card');
                    }
                }
                window.addingToParentCode = null;
            }
        }
    } catch (e) {
        console.error(e);
        root.innerHTML = `<div class="empty-state">Failed to load groups.</div>`;
    }
}


let activeParentCode = null;
let activeParentName = '';
let activeParentType = '';
let currentPage = 1;

root.addEventListener('click', async e => {
    const header = e.target.closest('.node-header');
    const addB = e.target.closest('.add-btn');
    const card = e.target.closest('.node-card');

    if (addB) {
        e.stopPropagation();
        if (card) {
            const level = parseInt(card.dataset.level);
            const type = card.dataset.type;
            const parentCode = card.dataset.code;
            const showOnlyName = (level < DETAIL_LEVEL - 1);
            console.log('console',showOnlyName, level, parentCode);
            window.addingToParentCode = parentCode;
            const nextCode = await Helpers.getNextAccountCode(parentCode, level + 1);
            if (nextCode) openAccountModal(nextCode.next_acc_code, level + 1, showOnlyName);
        }
        return;
    }

    if (header) {
        // Toggle collapse
        const hasKids = card.querySelector('.node-children');
        if (hasKids) {
            const open = !card.classList.contains('collapsed');
            card.classList.toggle('collapsed', open);
            header.setAttribute('aria-expanded', String(!open));
            const chv = header.querySelector('.chevron:not(.leaf)');
            if (chv) chv.classList.toggle('open', !open);
        }

        // Highlight selection and fetch details if level 3
        document.querySelectorAll('.node-card.active').forEach(n => n.classList.remove('active'));
        card.classList.add('active');

        const level = parseInt(card.dataset.level);
        if (level === DETAIL_LEVEL - 1) {
            activeParentCode = card.dataset.code;
            activeParentName = card.dataset.name;
            activeParentType = card.dataset.type;
            currentPage = 1;
            document.getElementById('selected-group-name').textContent = activeParentName;
            document.getElementById('selected-group-code').textContent = activeParentCode;
            document.getElementById('selected-group-code').style.display = 'inline-block';
            document.getElementById('details-actions').style.display = 'flex';
            loadDetails();
        } else {
            activeParentCode = null;
            document.getElementById('selected-group-name').textContent = card.dataset.name + ` (Select a Level ${DETAIL_LEVEL - 1} subgroup)`;
            document.getElementById('selected-group-code').style.display = 'none';
            document.getElementById('details-actions').style.display = 'none';
            document.getElementById('details-tbody').innerHTML = `<tr><td colspan="5" class="empty-state">Select a level ${DETAIL_LEVEL - 1} group to view detail accounts.</td></tr>`;
            document.getElementById('details-pagination').style.display = 'none';
        }
    }
});

// Detail Table Functions
async function loadDetails() {
    if (!activeParentCode) return;
    const search = document.getElementById('details-search').value;
    try {
        const res = await fetch(`${GetDetailAccountsUrl}?parent_code=${activeParentCode}&search=${encodeURIComponent(search)}&page=${currentPage}`);
        const json = await res.json();

        const tbody = document.getElementById('details-tbody');
        if (json.success) {
            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="2" class="empty-state">No detail accounts found.</td></tr>`;
            } else {
                tbody.innerHTML = json.data.map(d => `
                    <tr>
                        <td style="font-family: var(--font-mono);">${d.code}</td>
                        <td style="font-weight: 500;">${d.name}</td>
                        <!-- <td>${d.type}</td>
                        <td>${d.city || '-'}</td>
                        <td class="text-right">${parseFloat(d.balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td> -->
                    </tr>
                `).join('');
            }

            // update pagination
            const pag = json.pagination;
            const pInfo = document.getElementById('page-info');
            const btnPrev = document.getElementById('btn-prev');
            const btnNext = document.getElementById('btn-next');

            if (pag.total > 0) {
                document.getElementById('details-pagination').style.display = 'flex';
                pInfo.textContent = `Page ${pag.current_page} of ${pag.pages} (${pag.total} total)`;
                btnPrev.disabled = !pag.has_prev;
                btnNext.disabled = !pag.has_next;
            } else {
                document.getElementById('details-pagination').style.display = 'none';
            }
        }
    } catch (e) {
        console.error(e);
    }
}

document.getElementById('details-search').addEventListener('input', debounce(() => {
    currentPage = 1;
    loadDetails();
}, 300));

document.getElementById('btn-prev').addEventListener('click', () => {
    currentPage--;
    loadDetails();
});

document.getElementById('btn-next').addEventListener('click', () => {
    currentPage++;
    loadDetails();
});

document.getElementById('btn-add-detail').addEventListener('click', async () => {
    if (!activeParentCode) return;
    console.log(activeParentCode);
    window.addingToParentCode = activeParentCode;
    const nextCode = await Helpers.getNextAccountCode(activeParentCode, DETAIL_LEVEL);
    if (nextCode) openAccountModal(nextCode.next_acc_code, DETAIL_LEVEL, false);
});

function debounce(func, timeout = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, timeout);
    };
}

document.getElementById('accModalSave').addEventListener('click', () => {
    setTimeout(() => {
        // Just reload the whole tree or details table to keep it simple
        loadTree();
        if (activeParentCode) {
            loadDetails();
        }
    }, 1000); // Wait for API to finish saving
});

// Init
loadTree();

