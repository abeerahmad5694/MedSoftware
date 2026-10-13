
// ── Theme Definitions ──
const themes = [
    { id: 'blue', name: 'Default Ocean', color: '#2563eb', desc: 'Cool blue, light canvas' },
    { id: 'dark', name: 'Eclipse Dark', color: '#1e293b', desc: 'Deep dark workspace', border: true },
    { id: 'emerald', name: 'Emerald Grove', color: '#059669', desc: 'Fresh green tones' },
    { id: 'royal', name: 'Royal Velvet', color: '#7c3aed', desc: 'Rich purple accents' },
    { id: 'amber', name: 'Sunset Amber', color: '#d97706', desc: 'Warm golden palette' },
    { id: 'rose', name: 'Rose Quartz', color: '#e11d48', desc: 'Elegant pink accent' },
    { id: 'teal', name: 'Midnight Teal', color: '#0d9488', desc: 'Dark teal immersion', border: true },
    { id: 'slate', name: 'Slate Minimal', color: '#94a3b8', desc: 'Light neutral sidebar' },
    { id: 'pink', name: 'Pink Neon Rose', color: '#FF007F', desc: 'Neon pink accents' },
];

let currentTheme = localStorage.getItem('erp-theme') || 'blue';

function applyTheme(id) {
    document.documentElement.setAttribute('data-theme', id);
    currentTheme = id;
    localStorage.setItem('erp-theme', id);
    renderThemeList();
}

function renderThemeList() {
    const el = document.getElementById('themeList');
    if (!el) return;
    el.innerHTML = themes.map(t => `
                <div class="theme-swatch ${t.id === currentTheme ? 'active' : ''}" onclick="applyTheme('${t.id}')">
                    <div class="theme-dot" style="background:${t.color};${t.border ? 'box-shadow:inset 0 0 0 1px rgba(255,255,255,.15);' : ''}">
                        <i class="fa-solid fa-check check"></i>
                    </div>
                    <div>
                        <div class="text-sm font-semibold text-[var(--text-main)]">${t.name}</div>
                        <div class="text-[0.625rem] text-[var(--text-muted)]">${t.desc}</div>
                    </div>
                </div>
            `).join('');
}

// ── Theme Panel ──
function openThemePanel() {
    renderThemeList();
    const panel = document.getElementById('themePanel');
    if (panel) panel.classList.add('open');
}
function closeThemePanel() {
    const panel = document.getElementById('themePanel');
    if (panel) panel.classList.remove('open');
}

// ── Sub-menu toggle ──
function toggleSub(btn) {
    const parent = btn.closest('.sub-parent');
    if (!parent) return;
    const wasOpen = parent.classList.contains('open');
    document.querySelectorAll('.sub-parent').forEach(el => el.classList.remove('open'));
    if (!wasOpen) parent.classList.add('open');
}

// ── Mobile sidebar ──
function toggleMobileSidebar() {
    const sb = document.getElementById('sidebar');
    const ov = document.getElementById('mobileOverlay');
    if (sb) sb.classList.toggle('mobile-open');
    if (ov) ov.classList.toggle('active');
}

// ── Active nav highlight ──
document.querySelectorAll('.nav-item:not(button)').forEach(item => {
    item.addEventListener('click', function (e) {
        if (this.closest('.sub-parent') && this.tagName === 'BUTTON') return;
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        this.classList.add('active');
    });
});

// ── Keyboard shortcut for search ──
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const input = document.querySelector('.sb-search input');
        const sb = document.getElementById('sidebar');
        // On mobile, open sidebar first
        if (window.innerWidth < 769 && sb) {
            sb.classList.add('mobile-open');
            const ov = document.getElementById('mobileOverlay');
            if (ov) ov.classList.add('active');
        }
        if (input) setTimeout(() => input.focus(), 100);
    }
    if (e.key === 'Escape') {
        closeThemePanel();
    }
});

// ── Init Theme ──
applyTheme(currentTheme);


// ═══════════════════════════════════════════════════════════════════
// ── Global Toast Notification System (100% Robust Error Handling) ──
// ═══════════════════════════════════════════════════════════════════
window.showToast = function(msg, type = "info", duration = 4000) {
    try {
        let container = document.getElementById('global-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'global-toast-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '999999';
            container.style.display = 'flex';
            container.style.flexDirection = 'column';
            container.style.gap = '10px';
            container.style.pointerEvents = 'none';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.style.pointerEvents = 'auto';
        toast.style.display = 'flex';
        toast.style.alignItems = 'center';
        toast.style.gap = '10px';
        toast.style.padding = '12px 18px';
        toast.style.borderRadius = '8px';
        toast.style.fontSize = '13px';
        toast.style.fontWeight = '600';
        toast.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        toast.style.boxShadow = '0 10px 25px -5px rgba(0,0,0,0.3), 0 8px 10px -6px rgba(0,0,0,0.2)';
        toast.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        toast.style.transform = 'translateX(100%)';
        toast.style.opacity = '0';
        toast.style.cursor = 'pointer';

        // Color & Icon Configuration
        let bg = '#1e293b';
        let color = '#ffffff';
        let iconHtml = '<i class="fa-solid fa-circle-info" style="font-size: 16px; color: #38bdf8;"></i>';

        if (type === 'success') {
            bg = '#065f46';
            color = '#ecfdf5';
            iconHtml = '<i class="fa-solid fa-circle-check" style="font-size: 16px; color: #34d399;"></i>';
        } else if (type === 'error') {
            bg = '#991b1b';
            color = '#fef2f2';
            iconHtml = '<i class="fa-solid fa-circle-exclamation" style="font-size: 16px; color: #f87171;"></i>';
        } else if (type === 'warning') {
            bg = '#92400e';
            color = '#fffbeb';
            iconHtml = '<i class="fa-solid fa-triangle-exclamation" style="font-size: 16px; color: #fbbf24;"></i>';
        }

        toast.style.background = bg;
        toast.style.color = color;
        toast.innerHTML = `
            ${iconHtml}
            <span style="flex: 1; line-height: 1.4;">${msg}</span>
            <i class="fa-solid fa-xmark" style="opacity: 0.6; font-size: 12px; margin-left: 8px;"></i>
        `;

        container.appendChild(toast);

        // Slide in
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });

        // Click to dismiss
        const dismissToast = () => {
            toast.style.transform = 'translateX(100%)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        };
        toast.addEventListener('click', dismissToast);

        // Auto dismiss
        setTimeout(dismissToast, duration);
    } catch (e) {
        console.error('Toast Render Error:', e, msg);
        alert(msg);
    }
};


// ═══════════════════════════════════════════════════════════════════
// ── Company Configurations API Loader & Window Storage ──
// ═══════════════════════════════════════════════════════════════════
window.companyConfigurations = null;

window.loadCompanyConfigurations = async function() {
    const apiUrl = '/configuration/api/get-config/';
    try {
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            let errorDetail = `Server returned status ${response.status} (${response.statusText})`;
            try {
                const errData = await response.json();
                if (errData && errData.message) {
                    errorDetail = errData.message;
                }
            } catch (_) {}
            throw new Error(errorDetail);
        }

        const data = await response.json();

        if (data && data.success) {
            // Store configuration into window object as requested
            window.companyConfigurations = data.config || {};
            // Attach metadata and default accounts for seamless accessibility
            window.companyConfigurations._meta = {
                company: data.company || null,
                branch: data.branch || null,
                default_accounts: data.default_accounts || {}
            };

            // Dispatch global event in case other components/pages are listening
            window.dispatchEvent(new CustomEvent('companyConfigurationsLoaded', {
                detail: window.companyConfigurations
            }));
            
            console.log('✅ [CompanyConfigurations Loaded]:', window.companyConfigurations);
        } else {
            const msg = (data && data.message) ? data.message : 'Unknown configuration error returned from server.';
            throw new Error(msg);
        }
    } catch (error) {
        console.error('❌ [CompanyConfigurations API Error]:', error);
        window.showToast(`Configuration Error: ${error.message || error}`, 'error', 6000);
    }
};


// Helper function to get default account code by key with fallback
window.getDefaultAccount = function(key, fallback = 112000001) {
    const accounts = window.companyConfigurations?._meta?.default_accounts || {};
    return accounts[key] || fallback;
};

// ── Document Ready Handler ──
document.addEventListener('DOMContentLoaded', () => {
    // Automatically load company configurations on page load
    window.loadCompanyConfigurations();
});






document.addEventListener("mouseover", function (e) {
  const input = e.target.closest(".cart-input, .input-flat");

  if (!input || !input.value) return;

  // Check whether the input content is actually overflowing
  if (input.scrollWidth <= input.clientWidth) return;

  const tooltip = document.createElement("div");

  tooltip.className = "cart-value-tooltip";
  tooltip.textContent = input.value;

  document.body.appendChild(tooltip);

  const rect = input.getBoundingClientRect();

  tooltip.style.display = "block";
  tooltip.style.left = `${rect.left}px`;
  tooltip.style.top = `${rect.bottom + 8}px`;

  input._cartTooltip = tooltip;
});

document.addEventListener("mouseout", function (e) {
  const input = e.target.closest(".cart-input, .input-flat");

  if (!input) return;

  if (input._cartTooltip) {
    input._cartTooltip.remove();
    input._cartTooltip = null;
  }
});
