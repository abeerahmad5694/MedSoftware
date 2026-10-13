(() => {
    const root = document.getElementById('dashboardRoot');
    if (!root) return;

    const periodButtons = Array.from(root.querySelectorAll('[data-period]'));
    const refreshButton = root.querySelector('#refreshDashboard');
    const statusElement = root.querySelector('#dash-status');
    const chartSvg = root.querySelector('#weekChart');
    const chartEmpty = root.querySelector('#chart-empty');
    const currencySymbol = (root.dataset.currencySymbol || 'Rs').trim();
    const numberFormat = new Intl.NumberFormat('en-PK', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
    let selectedPeriod = root.dataset.defaultPeriod || 'today';
    let requestController = null;
    let hasLoaded = false;
    let latestChartData = null;
    const svgNamespace = 'http://www.w3.org/2000/svg';

    const formatNumber = (value) => {
        const number = Number(value || 0);
        return numberFormat.format(Number.isFinite(number) ? number : 0);
    };

    const formatMoney = (value) => `${currencySymbol} ${formatNumber(value)}`;

    const setText = (selector, value) => {
        const element = root.querySelector(selector);
        if (element) element.textContent = value;
    };

    const setStatus = (message, isError = false) => {
        if (!statusElement) return;
        statusElement.classList.toggle('is-error', isError);
        const dot = document.createElement('span');
        dot.className = 'dash-status-dot';
        dot.setAttribute('aria-hidden', 'true');
        statusElement.replaceChildren(dot, document.createTextNode(message));
    };

    const showInitialLoadError = () => {
        ['#receivables-list', '#payables-list', '#top-products-list', '#payable-reminders-list', '#low-stock-list', '#recent-vouchers-list'].forEach((selector) => {
            const container = root.querySelector(selector);
            if (container) {
                container.replaceChildren(makeElement('li', 'dash-empty-state', 'Data is unavailable. Please refresh to try again.'));
            }
        });
        if (chartEmpty) {
            chartEmpty.hidden = false;
            chartEmpty.textContent = 'Trend data is unavailable.';
        }
    };

    const setActivePeriod = (period) => {
        selectedPeriod = period;
        periodButtons.forEach((button) => {
            button.setAttribute('aria-pressed', String(button.dataset.period === period));
        });
    };

    const setLoading = (loading) => {
        if (refreshButton) {
            refreshButton.classList.toggle('is-loading', loading);
            refreshButton.disabled = loading;
        }
        root.setAttribute('aria-busy', String(loading));
    };

    const makeElement = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined && text !== null) element.textContent = String(text);
        return element;
    };

    const renderAccountList = (items, container, reportUrl, reminderMode = false) => {
        if (!container) return;
        container.replaceChildren();

        if (!items || items.length === 0) {
            const empty = makeElement('li', 'dash-empty-state', 'No outstanding balances to show.');
            container.appendChild(empty);
            return;
        }

        items.forEach((item) => {
            const row = document.createElement('li');
            const accountInfo = makeElement('span', 'dash-account-info');
            accountInfo.appendChild(makeElement('span', 'dash-account-name', item.name || `Account ${item.code}`));
            accountInfo.appendChild(makeElement('span', 'dash-account-code', `Account ${item.code}`));

            let left;
            if (reportUrl) {
                left = makeElement('a', reminderMode ? 'dash-reminder-account' : 'dash-reminder-account');
                left.href = reportUrl;
                left.appendChild(accountInfo);
            } else {
                left = accountInfo;
            }
            row.appendChild(left);

            if (reminderMode && reportUrl) {
                const review = makeElement('a', 'dash-reminder-action', 'Review');
                review.href = reportUrl;
                review.appendChild(makeElement('i', 'fa-solid fa-arrow-up-right-from-square'));
                review.lastElementChild.setAttribute('aria-hidden', 'true');
                row.appendChild(review);
            } else {
                row.appendChild(makeElement('strong', 'dash-row-amount', formatMoney(item.balance)));
            }
            container.appendChild(row);
        });
    };

    const renderTopProducts = (items) => {
        const container = root.querySelector('#top-products-list');
        if (!container) return;
        container.replaceChildren();

        if (!items || items.length === 0) {
            container.appendChild(makeElement('li', 'dash-empty-state', 'No product sales in this period.'));
            return;
        }

        const largestSale = Math.max(...items.map((item) => Number(item.revenue || 0)), 1);
        items.forEach((item, index) => {
            const row = document.createElement('li');
            const main = makeElement('div', 'dash-product-main');
            main.appendChild(makeElement('span', 'dash-rank-number', String(index + 1).padStart(2, '0')));

            const info = makeElement('span', 'dash-product-info');
            info.appendChild(makeElement('span', 'dash-product-name', item.name || 'Unnamed product'));
            info.appendChild(makeElement('span', 'dash-product-meta', `${formatNumber(item.qty)} sold`));
            const track = makeElement('span', 'dash-product-bar-track');
            const bar = makeElement('span', 'dash-product-bar');
            bar.style.width = `${Math.max(4, (Number(item.revenue || 0) / largestSale) * 100)}%`;
            track.appendChild(bar);
            info.appendChild(track);
            main.appendChild(info);

            row.appendChild(main);
            row.appendChild(makeElement('strong', 'dash-row-amount', formatMoney(item.revenue)));
            container.appendChild(row);
        });
    };

    const renderPayableReminders = (items) => {
        const container = root.querySelector('#payable-reminders-list');
        if (!container) return;
        container.replaceChildren();

        if (!items || items.length === 0) {
            container.appendChild(makeElement('li', 'dash-empty-state', 'No supplier balances need follow-up.'));
            return;
        }

        const reportUrl = root.dataset.payablesUrl || '';
        items.forEach((item) => {
            const row = document.createElement('li');
            const account = makeElement('span', 'dash-account-info');
            account.appendChild(makeElement('span', 'dash-account-name', item.name || `Account ${item.code}`));
            account.appendChild(makeElement('span', 'dash-account-code', `Account ${item.code}`));

            if (reportUrl) {
                const link = makeElement('a', 'dash-reminder-account');
                link.href = reportUrl;
                link.appendChild(account);
                row.appendChild(link);
            } else {
                row.appendChild(account);
            }
            row.appendChild(makeElement('strong', 'dash-row-amount', formatMoney(item.balance)));
            if (reportUrl) {
                const review = makeElement('a', 'dash-reminder-action', 'Review');
                review.href = reportUrl;
                const icon = makeElement('i', 'fa-solid fa-arrow-up-right-from-square');
                icon.setAttribute('aria-hidden', 'true');
                review.appendChild(icon);
                row.appendChild(review);
            }
            container.appendChild(row);
        });
    };

    const renderStockAlerts = (items) => {
        const container = root.querySelector('#low-stock-list');
        if (!container) return;
        container.replaceChildren();

        if (!items || items.length === 0) {
            container.appendChild(makeElement('li', 'dash-empty-state', 'Stock levels are looking good.'));
            return;
        }

        items.forEach((item) => {
            const row = document.createElement('li');
            const info = makeElement('span', 'dash-stock-info');
            info.appendChild(makeElement('span', 'dash-stock-name', item.name || `Item ${item.inv_id}`));
            info.appendChild(makeElement('span', 'dash-stock-meta', `Reorder at ${formatNumber(item.reorder)} ${item.unit || 'units'}`));
            row.appendChild(info);

            const balance = Number(item.balance || 0);
            const badge = makeElement(
                'span',
                `dash-stock-status${balance <= 0 ? ' is-out' : ''}`,
                balance <= 0 ? 'Out of stock' : `${formatNumber(balance)} left`
            );
            row.appendChild(badge);
            container.appendChild(row);
        });
    };

    const renderVouchers = (items) => {
        const container = root.querySelector('#recent-vouchers-list');
        if (!container) return;
        container.replaceChildren();

        if (!items || items.length === 0) {
            container.appendChild(makeElement('li', 'dash-empty-state', 'No ledger vouchers in this period.'));
            return;
        }

        items.forEach((item) => {
            const row = document.createElement('li');
            const type = (item.type || '').toUpperCase();
            let typeClass = 'dash-voucher-type';
            if (type === 'CP' || type === 'BP') typeClass += ' is-payment';
            if (type === 'BR' || type === 'BP') typeClass += ' is-bank';
            row.appendChild(makeElement('span', typeClass, type || '—'));

            const info = makeElement('span', 'dash-voucher-info');
            info.appendChild(makeElement('span', 'dash-voucher-name', item.description || 'Voucher'));
            info.appendChild(makeElement('span', 'dash-voucher-meta', `${type || 'Voucher'}-${item.number} · ${item.time} · Account ${item.account}`));
            row.appendChild(info);
            row.appendChild(makeElement('strong', 'dash-voucher-amount', formatMoney(item.amount)));
            container.appendChild(row);
        });
    };

    const compactMoney = (value) => {
        const compact = new Intl.NumberFormat('en-PK', {
            notation: 'compact',
            maximumFractionDigits: 1
        }).format(Number(value || 0));
        return `${currencySymbol} ${compact}`;
    };

    const renderChart = (chartData) => {
        if (!chartSvg) return;
        latestChartData = chartData;
        chartSvg.replaceChildren();

        const labels = chartData?.labels || [];
        const sales = chartData?.sales || [];
        const purchases = chartData?.purchases || [];
        const hasActivity = [...sales, ...purchases].some((value) => Number(value || 0) !== 0);
        if (chartEmpty) chartEmpty.hidden = hasActivity;
        if (labels.length === 0) return;

        const height = 250;
        const bounds = chartSvg.getBoundingClientRect();
        const width = Math.max(340, bounds.height ? height * bounds.width / bounds.height : 760);
        chartSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        const padding = { top: 12, right: 12, bottom: 31, left: 66 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const allValues = [...sales, ...purchases].map((value) => Number(value || 0));
        const minValue = Math.min(0, ...allValues);
        const maxValue = Math.max(1, ...allValues);
        const valueRange = maxValue - minValue || 1;
        const xAt = (index) => padding.left + (labels.length <= 1 ? plotWidth / 2 : (index / (labels.length - 1)) * plotWidth);
        const yAt = (value) => padding.top + ((maxValue - Number(value || 0)) / valueRange) * plotHeight;

        const addSvgElement = (tag, attributes = {}, text = null) => {
            const element = document.createElementNS(svgNamespace, tag);
            Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, String(value)));
            if (text !== null) element.textContent = String(text);
            chartSvg.appendChild(element);
            return element;
        };

        const gridSteps = 4;
        for (let step = 0; step <= gridSteps; step += 1) {
            const value = maxValue - (valueRange * step / gridSteps);
            const y = padding.top + (plotHeight * step / gridSteps);
            addSvgElement('line', {
                x1: padding.left,
                y1: y,
                x2: width - padding.right,
                y2: y,
                class: 'dash-chart-gridline'
            });
            addSvgElement('text', {
                x: padding.left - 9,
                y: y + 3.5,
                'text-anchor': 'end',
                class: 'dash-chart-axis-label'
            }, compactMoney(value));
        }

        const series = [
            { values: sales, lineClass: 'dash-chart-line-sales', pointClass: 'dash-chart-point-sales' },
            { values: purchases, lineClass: 'dash-chart-line-purchases', pointClass: 'dash-chart-point-purchases' }
        ];
        series.forEach(({ values, lineClass, pointClass }) => {
            if (!values.length) return;
            const points = values.map((value, index) => `${xAt(index)},${yAt(value)}`);
            addSvgElement('polyline', {
                points: points.join(' '),
                class: lineClass
            });
            if (labels.length <= 8) {
                values.forEach((value, index) => {
                    addSvgElement('circle', {
                        cx: xAt(index),
                        cy: yAt(value),
                        r: 3.5,
                        class: pointClass
                    });
                });
            }
        });

        const tickCount = Math.min(7, labels.length);
        const labelIndexes = new Set();
        for (let tick = 0; tick < tickCount; tick += 1) {
            labelIndexes.add(tickCount === 1 ? 0 : Math.round(tick * (labels.length - 1) / (tickCount - 1)));
        }
        labelIndexes.forEach((index) => {
            addSvgElement('text', {
                x: xAt(index),
                y: height - 7,
                'text-anchor': index === 0 ? 'start' : index === labels.length - 1 ? 'end' : 'middle',
                class: 'dash-chart-axis-label'
            }, labels[index]);
        });

        chartSvg.setAttribute('aria-label', `Sales and purchases trend. ${labels.length} points for the selected period.`);
    };

    const renderDashboard = (data) => {
        const kpi = data.kpi || {};
        const flow = data.cash_flow || {};
        const pnl = data.profit_loss || {};
        const balances = data.balances || {};
        const periodLabel = data.period_label || 'Selected period';

        setText('#dash-today', data.today || '');
        setText('#kpi-sales', formatMoney(kpi.sales));
        setText('#kpi-sales-bills', formatNumber(kpi.sales_bills));
        setText('#kpi-purchases', formatMoney(kpi.purchases));
        setText('#kpi-purchase-bills', formatNumber(kpi.purchase_bills));
        setText('#kpi-purchase-paid', formatMoney(kpi.purchase_paid));
        setText('#kpi-expenses', formatMoney(kpi.expenses));
        setText('#kpi-expense-entries', formatNumber(kpi.expense_entries));
        setText('#kpi-low-stock', formatNumber(kpi.low_stock_count));

        setText('#pnl-profit', formatMoney(pnl.profit));
        setText('#pnl-profit-count', formatNumber(pnl.profit_items));
        setText('#pnl-loss', formatMoney(pnl.loss));
        setText('#pnl-loss-count', formatNumber(pnl.loss_items));
        setText('#pnl-cost-to-cost', formatMoney(pnl.cost_to_cost));
        setText('#pnl-cost-count', formatNumber(pnl.cost_to_cost_items));

        setText('#flow-cash-received', formatMoney(flow.cash_received));
        setText('#flow-cash-paid', formatMoney(flow.cash_paid));
        setText('#flow-bank-received', formatMoney(flow.bank_received));
        setText('#flow-bank-paid', formatMoney(flow.bank_paid));

        setText('#balance-receivable-total', formatMoney(balances.receivable_total));
        setText('#balance-receivable-count', formatNumber(balances.receivable_count));
        setText('#balance-payable-total', formatMoney(balances.payable_total));
        setText('#balance-payable-count', formatNumber(balances.payable_count));
        setText('#stock-count-label', `${formatNumber(kpi.low_stock_count)} items`);

        root.querySelectorAll('.js-period-label').forEach((element) => {
            element.textContent = periodLabel;
        });
        setText('#chart-period-label', periodLabel);
        setText('#cash-period-label', periodLabel);

        renderChart(data.chart || {});
        renderTopProducts(data.top_products || []);
        renderAccountList(
            balances.receivables || [],
            root.querySelector('#receivables-list'),
            root.dataset.receivablesUrl || ''
        );
        renderAccountList(
            balances.payables || [],
            root.querySelector('#payables-list'),
            root.dataset.payablesUrl || ''
        );
        renderPayableReminders(balances.payables || []);
        renderStockAlerts(data.low_stock || []);
        renderVouchers(data.recent_vouchers || []);
    };

    const loadDashboard = async (period = selectedPeriod) => {
        if (requestController) requestController.abort();
        const controller = new AbortController();
        requestController = controller;
        setActivePeriod(period);
        setLoading(true);
        setStatus(`Loading ${period === '7_days' ? 'the last 7 days' : period === 'this_month' ? 'this month' : 'today'}…`);

        const url = new URL(root.dataset.statsUrl, window.location.href);
        url.searchParams.set('period', period);

        try {
            const response = await fetch(url.toString(), {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: { 'Accept': 'application/json' },
                signal: controller.signal
            });
            if (!response.ok) {
                throw new Error(response.status === 403 ? 'You no longer have permission to view this dashboard.' : 'Dashboard data could not be loaded.');
            }

            const data = await response.json();
            if (!data.success) throw new Error(data.message || 'Dashboard data could not be loaded.');

            setActivePeriod(data.period || period);
            renderDashboard(data);
            hasLoaded = true;
            setStatus(`Updated for ${data.period_label || 'the selected period'}. Balances are as of ${data.date_to || 'today'}.`);
        } catch (error) {
            if (error.name === 'AbortError') return;
            if (!hasLoaded) showInitialLoadError();
            setStatus(error.message || 'Dashboard data could not be loaded. Please try again.', true);
        } finally {
            if (requestController === controller) {
                setLoading(false);
                requestController = null;
            }
        }
    };

    const chartWrap = root.querySelector('.dash-chart-wrap');
    if (chartWrap && 'ResizeObserver' in window) {
        let resizeFrame = 0;
        const chartResizeObserver = new ResizeObserver(() => {
            if (!latestChartData) return;
            cancelAnimationFrame(resizeFrame);
            resizeFrame = requestAnimationFrame(() => renderChart(latestChartData));
        });
        chartResizeObserver.observe(chartWrap);
    }

    periodButtons.forEach((button) => {
        button.addEventListener('click', () => {
            if (button.dataset.period !== selectedPeriod) loadDashboard(button.dataset.period);
        });
    });

    if (refreshButton) {
        refreshButton.addEventListener('click', () => loadDashboard(selectedPeriod));
    }

    setActivePeriod(selectedPeriod);
    loadDashboard(selectedPeriod);
})();
