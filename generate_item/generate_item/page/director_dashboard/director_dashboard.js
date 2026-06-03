frappe.pages['director-dashboard'].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Director Dashboard',
        single_column: true
    });

    // ── Chart.js CDN ──────────────────────────────────────────────────────────
    if (!window.Chart) {
        const script       = document.createElement('script');
        script.src         = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        document.head.appendChild(script);
    }

    // ── Page-level dropdown (Purchase / Sales) ────────────────────────────────
    const view_selector = page.add_field({
        label:     'Select View',
        fieldtype: 'Select',
        fieldname: 'view_type',
        options:   ['Purchase', 'Sales'],
        default:   'Purchase',
        change() { handle_dashboard_switch(view_selector.get_value()); }
    });

    // ── Filters ───────────────────────────────────────────────────────────────
    const from_date = page.add_field({
        label:    'From Date',
        fieldtype: 'Date',
        default:  frappe.datetime.month_start(),
        change:   load_data
    });

    const to_date = page.add_field({
        label:    'To Date',
        fieldtype: 'Date',
        default:  frappe.datetime.get_today(),
        change:   load_data
    });

    const branch = page.add_field({
        label:    'Branch',
        fieldtype: 'Link',
        options:  'Branch',
        change:   load_data
    });

    const type_selector = page.add_field({
        fieldtype: 'Select',
        fieldname: 'count_type',
        options:   ['Order Wise', 'Item Wise'],
        default:   'Order Wise',
        change:    load_data
    });

    // ── Bucket / colour definitions (5 buckets now) ───────────────────────────
    const BUCKETS = [
        { key: '0-7',   label: '0–7 d',   cls: 'bucket-0-7'   },
        { key: '8-14',  label: '8–14 d',  cls: 'bucket-8-14'  },
        { key: '15-21', label: '15–21 d', cls: 'bucket-15-21' },
        { key: '22-28', label: '22–28 d', cls: 'bucket-22-28' },
        { key: '28+',   label: '28+ d',   cls: 'bucket-28plus'},
    ];

    const BUCKET_COLORS = [
        'rgba(76,175,80,0.82)',    // 0-7   green
        'rgba(33,150,243,0.82)',   // 8-14  blue
        'rgba(255,152,0,0.82)',    // 15-21 orange
        'rgba(244,67,54,0.82)',    // 22-28 red
        'rgba(156,39,176,0.82)',   // 28+   purple
    ];

    // ── Styles ────────────────────────────────────────────────────────────────
    const styles = `<style>
        .dir-dashboard { padding: 20px; }

        /*
         * Grid: 5-card bucket area | doc-type label | bar chart
         * Bucket area is wider (380px) to accommodate the 5th card cleanly.
         */
        .dir-section-card {
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            margin-bottom: 24px;
            display: grid;
            grid-template-columns: 380px 130px 1fr;
            align-items: center;
            min-height: 210px;
            overflow: hidden;
        }

        /* ── Left: bucket cards in a responsive grid ──────────────── */
        .dir-bucket-grid {
            display: grid;
            /*
             * 5 cards: first row 3 cards, second row 2 centred.
             * auto-fit lets the grid reflow on narrow screens.
             */
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding: 14px;
        }
        /* Centre the last two cards when they form a second row alone */
        .dir-bucket-grid .dir-bucket-card:nth-child(4) { grid-column: 1; }
        .dir-bucket-grid .dir-bucket-card:nth-child(5) { grid-column: 2; }

        .dir-bucket-card {
            background: var(--control-bg, #f5f5f5);
            border-radius: 8px;
            padding: 14px 6px;
            text-align: center;
            border: 1px solid var(--border-color);
            transition: transform 0.15s, box-shadow 0.15s;
            cursor: default;
        }
        .dir-bucket-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        .dir-bucket-card .bucket-range {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 5px;
        }
        .dir-bucket-card .bucket-count {
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
        }
        .dir-bucket-card .bucket-unit {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        /* Colour accents */
        .bucket-0-7    { border-top: 3px solid #4CAF50; }
        .bucket-0-7    .bucket-count { color: #2E7D32; }
        .bucket-8-14   { border-top: 3px solid #2196F3; }
        .bucket-8-14   .bucket-count { color: #1565C0; }
        .bucket-15-21  { border-top: 3px solid #FF9800; }
        .bucket-15-21  .bucket-count { color: #E65100; }
        .bucket-22-28  { border-top: 3px solid #F44336; }
        .bucket-22-28  .bucket-count { color: #B71C1C; }
        .bucket-28plus { border-top: 3px solid #9C27B0; }
        .bucket-28plus .bucket-count { color: #6A1B9A; }

        /* ── Centre label ─────────────────────────────────────────── */
        .dir-section-label {
            align-self: stretch;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 0;
            border-left:  1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
        }
        .dir-section-label .doc-type {
            font-size: 28px;
            font-weight: 700;
            color: var(--heading-color);
            letter-spacing: 2px;
        }
        .dir-section-label .doc-subtitle {
            font-size: 10px;
            color: var(--text-muted);
            text-align: center;
            padding: 0 6px;
        }
        .dir-section-label .total-badge {
            background: var(--primary);
            color: #fff;
            border-radius: 20px;
            padding: 3px 12px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        /* ── Right: chart ─────────────────────────────────────────── */
        .dir-chart-col {
            padding: 16px 20px;
            height: 220px;
            position: relative;
            box-sizing: border-box;
        }

        /* ── Loading ──────────────────────────────────────────────── */
        .dir-loading {
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            font-size: 13px;
            grid-column: 1 / -1;
            padding: 20px;
        }

        @media (max-width: 960px) {
            .dir-section-card {
                grid-template-columns: 1fr;
            }
            .dir-section-label {
                border-left: none; border-right: none;
                border-top: 1px solid var(--border-color);
                border-bottom: 1px solid var(--border-color);
                padding: 12px 0;
            }
            .dir-chart-col { height: 200px; }
            .dir-bucket-grid { grid-template-columns: repeat(3, 1fr); }
            .dir-bucket-grid .dir-bucket-card:nth-child(4),
            .dir-bucket-grid .dir-bucket-card:nth-child(5) { grid-column: auto; }
        }
    </style>`;

    // ── DOM ───────────────────────────────────────────────────────────────────
    $(`
        ${styles}
        <div class="dir-dashboard">

            <!-- MR -->
            <div class="dir-section-card" id="mr-section">
                <div class="dir-bucket-grid" id="mr-bucket-grid">
                    <div class="dir-loading">Loading…</div>
                </div>
                <div class="dir-section-label">
                    <div class="doc-type">MR</div>
                    <div class="doc-subtitle">Material Requests</div>
                    <div class="total-badge" id="mr-total-badge">—</div>
                </div>
                <div class="dir-chart-col">
                    <canvas id="mrPendingChart"></canvas>
                </div>
            </div>

            <!-- PO -->
            <div class="dir-section-card" id="po-section">
                <div class="dir-bucket-grid" id="po-bucket-grid">
                    <div class="dir-loading">Loading…</div>
                </div>
                <div class="dir-section-label">
                    <div class="doc-type">PO</div>
                    <div class="doc-subtitle">Purchase Orders</div>
                    <div class="total-badge" id="po-total-badge">—</div>
                </div>
                <div class="dir-chart-col">
                    <canvas id="poPendingChart"></canvas>
                </div>
            </div>

            <!-- PR -->
            <div class="dir-section-card" id="pr-section">
                <div class="dir-bucket-grid" id="pr-bucket-grid">
                    <div class="dir-loading">Loading…</div>
                </div>
                <div class="dir-section-label">
                    <div class="doc-type">PR</div>
                    <div class="doc-subtitle">Purchase Receipts</div>
                    <div class="total-badge" id="pr-total-badge">—</div>
                </div>
                <div class="dir-chart-col">
                    <canvas id="prPendingChart"></canvas>
                </div>
            </div>

        </div>
    `).appendTo(page.body);

    // ── Chart registry (for clean destroy-before-recreate) ────────────────────
    const charts = {};

    // ── Data loading ──────────────────────────────────────────────────────────
    function load_data() {
        const mode = (type_selector.get_value() || 'Order Wise');
        if (mode === 'Item Wise') {
            _call_api(
                'generate_item.generate_item.page.director_dashboard.director_dashboard.get_item_wise_data',
                render_item_wise
            );
        } else {
            _call_api(
                'generate_item.generate_item.page.director_dashboard.director_dashboard.get_dashboard_data',
                render_order_wise
            );
        }
    }

    function _call_api(method, cb) {
        frappe.call({
            method,
            args: {
                from_date: from_date.get_value() || '',
                to_date:   to_date.get_value()   || '',
                branch:    branch.get_value()     || '',
            },
            callback(r) { if (r.message) cb(r.message); }
        });
    }

    // ── Render helpers ────────────────────────────────────────────────────────
    function render_order_wise(data) {
        _wait_for_chart(() => {
            render_section('mr', data.pending_mr, 'MRs', 'mrPendingChart');
            render_section('po', data.pending_po, 'POs', 'poPendingChart');
            render_section('pr', data.pending_pr, 'PRs', 'prPendingChart');
        });
    }

    function render_item_wise(data) {
        _wait_for_chart(() => {
            render_section('mr', data.pending_mr, 'Items', 'mrPendingChart');
            render_section('po', data.pending_po, 'Items', 'poPendingChart');
            render_section('pr', data.pending_pr, 'Items', 'prPendingChart');
        });
    }

    /** Poll until Chart.js is available, then run callback. */
    function _wait_for_chart(fn) {
        if (window.Chart) { fn(); } else { setTimeout(() => _wait_for_chart(fn), 100); }
    }

    // ── Section renderer ──────────────────────────────────────────────────────
    function render_section(prefix, data, unit, chartId) {
        if (!data) return;

        const cardHtml = BUCKETS.map(b => {
            const count = (data[b.key] || {}).count || 0;
            return `
                <div class="dir-bucket-card ${b.cls}">
                    <div class="bucket-range">${b.label}</div>
                    <div class="bucket-count">${count}</div>
                    <div class="bucket-unit">${unit}</div>
                </div>`;
        }).join('');

        $(`#${prefix}-bucket-grid`).html(cardHtml);

        const total = BUCKETS.reduce((s, b) => s + ((data[b.key] || {}).count || 0), 0);
        $(`#${prefix}-total-badge`).text(`${total} Pending`);

        _render_bar_chart(chartId, data, unit);
    }

    // ── Bar chart renderer ────────────────────────────────────────────────────
    function _render_bar_chart(chartId, data, unit) {
        const el = document.getElementById(chartId);
        if (!el) return;

        const counts = BUCKETS.map(b => (data[b.key] || {}).count || 0);

        if (charts[chartId] && typeof charts[chartId].destroy === 'function') {
            charts[chartId].destroy();
        }

        charts[chartId] = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: {
                labels: BUCKETS.map(b => b.key),
                datasets: [{
                    label:           `Pending ${unit}`,
                    data:            counts,
                    backgroundColor: BUCKET_COLORS,
                    borderRadius:    6,
                    borderWidth:     0,
                    barThickness:    32,
                }]
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0, stepSize: 1 },
                        title: { display: true, text: `Count of ${unit}`, font: { size: 10 } }
                    },
                    x: {
                        title: { display: true, text: 'Pending Days Bucket', font: { size: 10 } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: items  => `${items[0].label} days pending`,
                            label: ctx    => `  ${ctx.raw} ${unit}`,
                        }
                    }
                }
            }
        });
    }

    // ── Boot ──────────────────────────────────────────────────────────────────
    setTimeout(load_data, 200);
};

// ── Top-level: switch between Purchase and Sales dashboards ──────────────────
function handle_dashboard_switch(value) {
    if      (value === 'Sales')    frappe.set_route('sales-performance-da');
    else if (value === 'Purchase') frappe.set_route('director-dashboard');
}