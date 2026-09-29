// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.pages['sales-order-time-rev'].on_page_load = function (wrapper) {
    frappe.sales_order_time_rev = new SalesOrderPhaseTimeDashboard(wrapper);
};

class SalesOrderPhaseTimeDashboard {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("Sales Order Phase Time Dashboard"),
            single_column: true,
        });

        this.filters = {
            period: "Last Month",
            from_date: null,
            to_date: null,
            branch: "",
            sales_order: "",
            customer: "",
        };

        this.controls = {};
        this.raw_rows = [];
        this.summary = {};
        this.search_query = "";
        this.sort_field = "so_date_raw";
        this.sort_order = "desc";
        this.current_page = 1;
        this.page_size = 25;

        // Initialize default dates from preset
        const dates = this.resolve_preset(this.filters.period);
        this.filters.from_date = dates.from_date;
        this.filters.to_date = dates.to_date;

        this.inject_styles();
        this.render_page_actions();
        this.render_shell();
        this.init_filter_controls();
        this.bind_events();
        this.load_data();
    }

    inject_styles() {
        if (document.getElementById("sopt-enterprise-styles")) return;
        const style = document.createElement("style");
        style.id = "sopt-enterprise-styles";
        style.textContent = `
            :root {
                --sopt-bg: #f8fafc;
                --sopt-surface: #ffffff;
                --sopt-surface-subtle: #f8fafc;
                --sopt-border: #e2e8f0;
                --sopt-border-strong: #cbd5e1;
                --sopt-text: #0f172a;
                --sopt-text-secondary: #475569;
                --sopt-muted: #64748b;
                --sopt-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
                --sopt-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
                --sopt-radius-sm: 6px;
                --sopt-radius-md: 10px;
                --sopt-radius-lg: 14px;
            }

            .sopt-page-wrap {
                max-width: 1720px;
                margin: 0 auto;
                padding: 14px 20px 60px;
                color: var(--sopt-text);
                font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
            }

            /* Hero / Header */
            .sopt-hero {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border-radius: var(--sopt-radius-lg);
                padding: 20px 26px;
                margin-bottom: 20px;
                color: #ffffff;
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
                position: relative;
                overflow: hidden;
            }

            .sopt-hero::after {
                content: "";
                position: absolute;
                right: -40px;
                top: -40px;
                width: 220px;
                height: 220px;
                background: radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, rgba(59, 130, 246, 0) 70%);
                pointer-events: none;
            }

            .sopt-hero-left {
                display: flex;
                align-items: center;
                gap: 16px;
                z-index: 1;
            }

            .sopt-hero-icon {
                width: 48px;
                height: 48px;
                border-radius: 12px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-size: 22px;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
                flex-shrink: 0;
            }

            .sopt-hero-title-group h1 {
                font-size: 21px;
                font-weight: 700;
                margin: 0 0 3px;
                letter-spacing: -0.01em;
                color: #ffffff;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .sopt-hero-title-group p {
                font-size: 13px;
                margin: 0;
                color: #94a3b8;
            }

            .sopt-hero-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                background: rgba(16, 185, 129, 0.18);
                color: #34d399;
                border: 1px solid rgba(52, 211, 153, 0.3);
                padding: 2px 8px;
                border-radius: 9999px;
            }

            .sopt-live-dot {
                width: 6px;
                height: 6px;
                background: #34d399;
                border-radius: 50%;
                animation: sopt-pulse 2s infinite ease-in-out;
            }

            @keyframes sopt-pulse {
                0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }
                70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(52, 211, 153, 0); }
                100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
            }

            .sopt-hero-actions {
                display: flex;
                align-items: center;
                gap: 8px;
                z-index: 1;
            }

            .sopt-hero-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 14px;
                border-radius: var(--sopt-radius-sm);
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                border: 1px solid transparent;
            }

            .sopt-hero-btn.primary {
                background: #3b82f6;
                color: #fff;
                box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);
            }

            .sopt-hero-btn.primary:hover {
                background: #2563eb;
                transform: translateY(-1px);
            }

            .sopt-hero-btn.outline {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.15);
            }

            .sopt-hero-btn.outline:hover {
                background: rgba(255, 255, 255, 0.15);
            }

            /* Filter Panel */
            .sopt-filter-card {
                background: var(--sopt-surface);
                border: 1px solid var(--sopt-border);
                border-radius: var(--sopt-radius-md);
                box-shadow: var(--sopt-shadow-sm);
                padding: 16px 20px 18px;
                margin-bottom: 22px;
            }

            .sopt-filter-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid #f1f5f9;
            }

            .sopt-filter-title {
                font-weight: 600;
                font-size: 13px;
                color: var(--sopt-text);
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .sopt-filter-title i {
                color: #6366f1;
            }

            .sopt-filter-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 14px 16px;
                align-items: end;
            }

            .sopt-filter-group {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .sopt-filter-label {
                font-size: 11px;
                font-weight: 600;
                color: var(--sopt-muted);
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }

            /* Number Cards Grid */
            .sopt-cards-grid {
                display: grid;
                grid-template-columns: repeat(6, 1fr);
                gap: 14px;
                margin-bottom: 24px;
            }

            @media (max-width: 1440px) {
                .sopt-cards-grid { grid-template-columns: repeat(3, 1fr); }
            }

            @media (max-width: 820px) {
                .sopt-cards-grid { grid-template-columns: repeat(2, 1fr); }
            }

            @media (max-width: 520px) {
                .sopt-cards-grid { grid-template-columns: 1fr; }
            }

            .sopt-card {
                background: var(--sopt-surface);
                border: 1px solid var(--sopt-border);
                border-radius: var(--sopt-radius-md);
                padding: 16px 16px 14px;
                box-shadow: var(--sopt-shadow-sm);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 144px;
                position: relative;
                overflow: hidden;
                transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, border-color 0.2s ease;
            }

            .sopt-card::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: var(--card-accent, #94a3b8);
            }

            .sopt-card:hover {
                transform: translateY(-3px);
                box-shadow: var(--sopt-shadow-md);
                border-color: var(--sopt-border-strong);
            }

            .sopt-card.phase-1 { --card-accent: #2563eb; --card-icon-bg: rgba(37, 99, 235, 0.1); --card-icon-color: #2563eb; }
            .sopt-card.phase-2 { --card-accent: #7c3aed; --card-icon-bg: rgba(124, 58, 237, 0.1); --card-icon-color: #7c3aed; }
            .sopt-card.phase-3 { --card-accent: #d97706; --card-icon-bg: rgba(217, 119, 6, 0.1); --card-icon-color: #d97706; }
            .sopt-card.phase-4 { --card-accent: #0284c7; --card-icon-bg: rgba(2, 132, 199, 0.1); --card-icon-color: #0284c7; }
            .sopt-card.phase-5 { --card-accent: #0891b2; --card-icon-bg: rgba(8, 145, 178, 0.1); --card-icon-color: #0891b2; }
            .sopt-card.phase-overall {
                --card-accent: #059669;
                --card-icon-bg: rgba(5, 150, 105, 0.1);
                --card-icon-color: #059669;
                background: linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%);
                border-color: #bbf7d0;
            }

            .sopt-card-top {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .sopt-card-tag {
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                padding: 2px 7px;
                border-radius: 4px;
                background: var(--card-icon-bg);
                color: var(--card-icon-color);
            }

            .sopt-card-icon-circle {
                width: 28px;
                height: 28px;
                border-radius: 8px;
                background: var(--card-icon-bg);
                color: var(--card-icon-color);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
            }

            .sopt-card-title {
                font-size: 11.5px;
                font-weight: 600;
                color: var(--sopt-muted);
                line-height: 1.35;
                min-height: 32px;
                margin-bottom: 6px;
            }

            .sopt-card-body {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
            }

            .sopt-card-num {
                font-size: 26px;
                font-weight: 800;
                color: var(--sopt-text);
                line-height: 1;
                letter-spacing: -0.02em;
            }

            .sopt-card-units-group {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }

            .sopt-card-unit {
                font-size: 11px;
                font-weight: 600;
                color: var(--sopt-muted);
                line-height: 1.1;
            }

            .sopt-card-days-pill {
                font-size: 10px;
                font-weight: 600;
                color: var(--card-icon-color, #475569);
                background: var(--card-icon-bg, rgba(71, 85, 105, 0.1));
                padding: 1px 5px;
                border-radius: 4px;
                width: fit-content;
                line-height: 1.2;
            }

            .sopt-pill-days {
                font-size: 10.5px;
                font-weight: 500;
                opacity: 0.82;
                margin-left: 3px;
            }

            .sopt-card-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 11px;
                color: var(--sopt-muted);
                padding-top: 6px;
                border-top: 1px dashed #f1f5f9;
            }

            .sopt-card-count {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-weight: 500;
                color: #475569;
            }

            .sopt-card-subbadge {
                font-size: 10px;
                font-weight: 700;
                color: #047857;
                background: #d1fae5;
                padding: 1px 6px;
                border-radius: 4px;
            }

            /* Table Section */
            .sopt-table-section {
                background: var(--sopt-surface);
                border: 1px solid var(--sopt-border);
                border-radius: var(--sopt-radius-md);
                box-shadow: var(--sopt-shadow-sm);
                overflow: hidden;
                margin-bottom: 24px;
            }

            .sopt-table-header-bar {
                padding: 16px 22px;
                background: #ffffff;
                border-bottom: 1px solid var(--sopt-border);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 14px;
            }

            .sopt-table-heading h3 {
                font-size: 16px;
                font-weight: 700;
                color: var(--sopt-text);
                margin: 0 0 3px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .sopt-table-heading span {
                font-size: 12px;
                color: var(--sopt-muted);
            }

            .sopt-table-legend {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }

            .sopt-legend-item {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                font-weight: 500;
                color: #475569;
            }

            .sopt-dur-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }
            .sopt-dur-dot.fast { background: #10b981; }
            .sopt-dur-dot.moderate { background: #3b82f6; }
            .sopt-dur-dot.extended { background: #f59e0b; }
            .sopt-dur-dot.overall { background: #059669; }

            .sopt-table-subtoolbar {
                padding: 10px 22px;
                background: #f8fafc;
                border-bottom: 1px solid var(--sopt-border);
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }

            .sopt-search-container {
                position: relative;
                width: 320px;
            }

            .sopt-search-input {
                width: 100%;
                height: 34px;
                padding: 6px 12px 6px 34px;
                font-size: 12px;
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                outline: none;
                transition: all 0.15s ease;
            }

            .sopt-search-input:focus {
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
            }

            .sopt-search-icon {
                position: absolute;
                left: 11px;
                top: 10px;
                font-size: 12px;
                color: #94a3b8;
            }

            /* Table Layout */
            .sopt-table-wrap {
                overflow-x: auto;
                width: 100%;
                max-height: 680px;
                position: relative;
            }

            .sopt-data-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                font-size: 12px;
                text-align: left;
            }

            .sopt-data-table thead tr.group-header th {
                background: #f1f5f9;
                color: #334155;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                padding: 9px 14px;
                border-bottom: 1px solid #cbd5e1;
                border-right: 1px solid #e2e8f0;
                position: sticky;
                top: 0;
                z-index: 4;
            }

            .sopt-data-table thead tr.group-header th.group-durations {
                background: #eef2ff;
                color: #3730a3;
                border-left: 2px solid #c7d2fe;
            }

            .sopt-data-table thead tr.col-header th {
                background: #f8fafc;
                color: #475569;
                font-size: 11.5px;
                font-weight: 600;
                padding: 10px 12px;
                border-bottom: 1px solid var(--sopt-border);
                border-right: 1px solid #f1f5f9;
                white-space: nowrap;
                position: sticky;
                top: 35px;
                z-index: 3;
                user-select: none;
            }

            .sopt-data-table thead tr.col-header th.sortable {
                cursor: pointer;
                transition: background 0.15s ease;
            }

            .sopt-data-table thead tr.col-header th.sortable:hover {
                background: #e2e8f0;
                color: #0f172a;
            }

            .sopt-data-table thead tr.col-header th.sortable .sort-icon {
                font-size: 10px;
                margin-left: 4px;
                opacity: 0.4;
            }

            .sopt-data-table thead tr.col-header th.sortable.sorted {
                color: #1e40af;
                background: #e0e7ff;
            }

            .sopt-data-table thead tr.col-header th.sortable.sorted .sort-icon {
                opacity: 1;
            }

            .sopt-data-table th.sticky-col,
            .sopt-data-table td.sticky-col {
                position: sticky;
                left: 0;
                background: #ffffff;
                z-index: 2;
                box-shadow: 3px 0 6px -2px rgba(0, 0, 0, 0.06);
                border-right: 2px solid #e2e8f0 !important;
            }

            .sopt-data-table thead tr.group-header th.sticky-col {
                z-index: 6;
                background: #f1f5f9;
            }

            .sopt-data-table thead tr.col-header th.sticky-col {
                z-index: 5;
                background: #f8fafc;
            }

            .sopt-data-table tbody tr {
                transition: background 0.12s ease;
            }

            .sopt-data-table tbody tr:hover {
                background: #f8fafc;
            }

            .sopt-data-table tbody tr:hover td.sticky-col {
                background: #f8fafc;
            }

            .sopt-data-table tbody td {
                padding: 10px 12px;
                border-bottom: 1px solid #f1f5f9;
                border-right: 1px solid #f8fafc;
                vertical-align: middle;
            }

            .sopt-data-table tbody td.col-border-group {
                border-left: 2px solid #e0e7ff;
            }

            .sopt-so-cell {
                display: flex;
                flex-direction: column;
                gap: 3px;
            }

            .sopt-so-link {
                font-size: 13px;
                font-weight: 700;
                color: #2563eb;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }

            .sopt-so-link:hover {
                color: #1d4ed8;
                text-decoration: underline;
            }

            .sopt-branch-pill {
                display: inline-block;
                font-size: 10px;
                font-weight: 600;
                background: #f1f5f9;
                color: #475569;
                border-radius: 4px;
                padding: 1px 6px;
                width: fit-content;
            }

            .sopt-cust-cell {
                display: flex;
                align-items: center;
                gap: 8px;
                max-width: 220px;
            }

            .sopt-cust-avatar {
                width: 26px;
                height: 26px;
                border-radius: 6px;
                background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
                color: #334155;
                font-size: 10px;
                font-weight: 700;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }

            .sopt-cust-name {
                font-weight: 500;
                color: var(--sopt-text);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sopt-dur-pill {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 11.5px;
                font-weight: 600;
                white-space: nowrap;
                border: 1px solid transparent;
            }

            .sopt-dur-pill.fast {
                background: #ecfdf5;
                color: #047857;
                border-color: #a7f3d0;
            }

            .sopt-dur-pill.moderate {
                background: #eff6ff;
                color: #1d4ed8;
                border-color: #bfdbfe;
            }

            .sopt-dur-pill.extended {
                background: #fffbeb;
                color: #b45309;
                border-color: #fde68a;
            }

            .sopt-dur-pill.overall {
                background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                color: #065f46;
                border-color: #6ee7b7;
                font-weight: 700;
                box-shadow: 0 1px 2px rgba(6, 95, 70, 0.08);
            }

            .sopt-dash {
                color: #cbd5e1;
                font-weight: 600;
                font-size: 14px;
                text-align: center;
                display: block;
            }

            .sopt-pagination-bar {
                padding: 12px 22px;
                background: #ffffff;
                border-top: 1px solid var(--sopt-border);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
                font-size: 12px;
                color: var(--sopt-muted);
            }

            .sopt-page-btn {
                border: 1px solid #cbd5e1;
                background: #ffffff;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
                color: #334155;
                cursor: pointer;
                transition: all 0.15s ease;
            }

            .sopt-page-btn:hover:not(:disabled) {
                background: #f1f5f9;
                border-color: #94a3b8;
            }

            .sopt-page-btn:disabled {
                opacity: 0.4;
                cursor: not-allowed;
            }

            .sopt-page-indicator {
                font-weight: 600;
                color: #0f172a;
                padding: 3px 10px;
                background: #f1f5f9;
                border-radius: 6px;
            }

            .sopt-empty-box {
                text-align: center;
                padding: 56px 20px;
                color: #64748b;
            }

            .sopt-empty-box i {
                font-size: 38px;
                color: #cbd5e1;
                margin-bottom: 12px;
            }

            .sopt-empty-box h4 {
                font-size: 15px;
                font-weight: 600;
                color: #0f172a;
                margin: 0 0 6px;
            }
        `;
        document.head.appendChild(style);
    }

    render_page_actions() {
        this.page.clear_actions();
        this.page.add_button(__("Refresh"), () => this.load_data(), "fa fa-refresh");
        this.page.add_button(__("Export CSV"), () => this.export_data(), "fa fa-download");
    }

    render_shell() {
        const body = $(this.page.body);
        body.empty();

        const html = `
            <div class="sopt-page-wrap">
                <!-- Executive Hero Header -->
                <div class="sopt-hero">
                    <div class="sopt-hero-left">
                        <div class="sopt-hero-icon">
                            <i class="fa fa-tachometer"></i>
                        </div>
                        <div class="sopt-hero-title-group">
                            <h1>
                                ${__("Sales Order Phase Time Dashboard")}
                                <span class="sopt-hero-badge"><span class="sopt-live-dot"></span> ${__("Live Metrics")}</span>
                            </h1>
                            <p>${__("Measure and track turnaround elapsed weeks across Sales Order approval, BOM release, Procurement, and Work Order issuance.")}</p>
                        </div>
                    </div>
                    <div class="sopt-hero-actions">
                        <button class="sopt-hero-btn outline sopt-btn-reload" type="button" title="${__("Reload data")}">
                            <i class="fa fa-refresh"></i> <span>${__("Refresh")}</span>
                        </button>
                        <button class="sopt-hero-btn primary sopt-btn-export" type="button" title="${__("Export CSV")}">
                            <i class="fa fa-download"></i> <span>${__("Export CSV")}</span>
                        </button>
                    </div>
                </div>

                <!-- Filters Card -->
                <div class="sopt-filter-card">
                    <div class="sopt-filter-header">
                        <div class="sopt-filter-title">
                            <i class="fa fa-sliders"></i>
                            <span>${__("Dashboard Filters & Parameters")}</span>
                        </div>
                        <div>
                            <button class="btn btn-xs btn-default sopt-btn-reset" type="button">
                                <i class="fa fa-undo"></i> ${__("Reset Filters")}
                            </button>
                        </div>
                    </div>
                    <div class="sopt-filter-grid">
                        <div class="sopt-filter-group" data-filter="period">
                            <label class="sopt-filter-label">${__("Period Preset")}</label>
                            <div class="sopt-control-period"></div>
                        </div>
                        <div class="sopt-filter-group" data-filter="from_date">
                            <label class="sopt-filter-label">${__("From Date")}</label>
                            <div class="sopt-control-from-date"></div>
                        </div>
                        <div class="sopt-filter-group" data-filter="to_date">
                            <label class="sopt-filter-label">${__("To Date")}</label>
                            <div class="sopt-control-to-date"></div>
                        </div>
                        <div class="sopt-filter-group" data-filter="branch">
                            <label class="sopt-filter-label">${__("Branch")}</label>
                            <div class="sopt-control-branch"></div>
                        </div>
                        <div class="sopt-filter-group" data-filter="sales_order">
                            <label class="sopt-filter-label">${__("Sales Order")}</label>
                            <div class="sopt-control-sales-order"></div>
                        </div>
                        <div class="sopt-filter-group" data-filter="customer">
                            <label class="sopt-filter-label">${__("Customer")}</label>
                            <div class="sopt-control-customer"></div>
                        </div>
                    </div>
                </div>

                <!-- Number Cards Grid (The 6 Phase Cards in Weeks) -->
                <div class="sopt-cards-grid" data-role="cards-container">
                    ${this.get_skeleton_cards_html()}
                </div>

                <!-- Main Timeline Table Section -->
                <div class="sopt-table-section">
                    <div class="sopt-table-header-bar">
                        <div class="sopt-table-heading">
                            <h3><i class="fa fa-list-alt text-primary"></i> ${__("Sales Order Phase Timeline")}</h3>
                            <span>${__("Calculated turnaround durations in weeks per Sales Order.")}</span>
                        </div>
                        <div class="sopt-table-legend">
                            <span class="sopt-legend-item"><span class="sopt-dur-dot fast"></span> ${__("≤ 1.00 Week (Fast)")}</span>
                            <span class="sopt-legend-item"><span class="sopt-dur-dot moderate"></span> ${__("1.00–4.00 Weeks")}</span>
                            <span class="sopt-legend-item"><span class="sopt-dur-dot extended"></span> ${__("> 4.00 Weeks (Watch)")}</span>
                            <span class="sopt-legend-item"><span class="sopt-dur-dot overall"></span> ${__("Total Turnaround")}</span>
                            <span class="badge badge-light ml-2" data-role="record-count" style="font-size: 11px; padding: 4px 8px;">0 Orders</span>
                        </div>
                    </div>

                    <div class="sopt-table-subtoolbar">
                        <div class="sopt-search-container">
                            <i class="fa fa-search sopt-search-icon"></i>
                            <input type="text" class="sopt-search-input" placeholder="${__("Search Sales Order, Customer, Branch...")}" data-role="table-search">
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-muted small">${__("Page size:")}</span>
                            <select class="form-control input-xs" style="width: auto; height: 32px;" data-role="page-size-select">
                                <option value="10">10 rows</option>
                                <option value="25" selected>25 rows</option>
                                <option value="50">50 rows</option>
                                <option value="100">100 rows</option>
                                <option value="999999">${__("Show All")}</option>
                            </select>
                        </div>
                    </div>

                    <div class="sopt-table-wrap">
                        <table class="sopt-data-table">
                            <thead>
                                <tr class="group-header">
                                    <th colspan="3" class="sticky-col">${__("Order Identification")}</th>
                                    <th colspan="6" class="group-durations" style="text-align: center;">
                                        <i class="fa fa-clock-o mr-1"></i> ${__("Calculated Phase Durations (Weeks & Days)")}
                                    </th>
                                </tr>
                                <tr class="col-header">
                                    <th class="sticky-col sortable" data-sort="sales_order">${__("Sales Order")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="customer_name">${__("Customer")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="so_date_raw">${__("SO Date")} <span class="sort-icon"></span></th>

                                    <!-- 1. SO Creation → SO Approved -->
                                    <th class="sortable col-border-group" data-sort="dur_so_cre_to_so_app">${__("SO Creation → SO Approved")} <span class="sort-icon"></span></th>

                                    <!-- 2. SO Approval → Last BOM Submitted -->
                                    <th class="sortable" data-sort="dur_so_app_to_last_bom_sub">${__("SO Approval → Last BOM Submitted")} <span class="sort-icon"></span></th>

                                    <!-- 3. Last BOM Submitted → Last Material Request Created on -->
                                    <th class="sortable" data-sort="dur_bom_sub_to_mr_cre">${__("Last BOM Submitted → Last Material Request Created on")} <span class="sort-icon"></span></th>

                                    <!-- 4. Last Material Request Submitted → Last Purchase Order Created on -->
                                    <th class="sortable" data-sort="dur_mr_sub_to_po_cre">${__("Last Material Request Submitted → Last Purchase Order Created on")} <span class="sort-icon"></span></th>

                                    <!-- 5. Last PO Approved → Last PR Submitted on -->
                                    <th class="sortable" data-sort="dur_po_app_to_last_pur_sub">${__("Last PO Approved → Last PR Submitted on")} <span class="sort-icon"></span></th>

                                    <!-- 6. Sales Order Created on → Work Order Submitted -->
                                    <th class="sortable" data-sort="dur_so_cre_to_wo_sub">${__("Sales Order Created on → Work Order Submitted")} <span class="sort-icon"></span></th>
                                </tr>
                            </thead>
                            <tbody data-role="table-body">
                                <tr>
                                    <td colspan="9" class="sopt-empty-box">
                                        <i class="fa fa-spinner fa-spin"></i>
                                        <h4>${__("Fetching Data...")}</h4>
                                        <div>${__("Loading Sales Orders and calculating milestone durations.")}</div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="sopt-pagination-bar">
                        <div data-role="footer-info">
                            ${__("Showing 0 to 0 of 0 records")}
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <button class="sopt-page-btn" data-role="prev-page" disabled><i class="fa fa-chevron-left mr-1"></i> ${__("Previous")}</button>
                            <span class="sopt-page-indicator" data-role="page-indicator">${__("Page 1 of 1")}</span>
                            <button class="sopt-page-btn" data-role="next-page" disabled>${__("Next")} <i class="fa fa-chevron-right ml-1"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        body.html(html);
    }

    init_filter_controls() {
        const body = $(this.page.body);

        // 1. Period Preset
        this.controls.period = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-period"),
            df: {
                fieldtype: "Select",
                options: ["Today", "Last Week", "Last Month", "Last Quarter", "Custom"],
                default: this.filters.period,
                input_class: "input-xs",
                change: () => {
                    const val = this.controls.period.get_value();
                    this.filters.period = val;
                    if (val !== "Custom") {
                        const dates = this.resolve_preset(val);
                        this.controls.from_date.set_value(dates.from_date);
                        this.controls.to_date.set_value(dates.to_date);
                    }
                    this.load_data();
                }
            },
            render_input: true,
        });

        // 2. From Date
        this.controls.from_date = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-from-date"),
            df: {
                fieldtype: "Date",
                default: this.filters.from_date,
                input_class: "input-xs",
                change: () => {
                    this.filters.from_date = this.controls.from_date.get_value();
                    this.load_data();
                }
            },
            render_input: true,
        });

        // 3. To Date
        this.controls.to_date = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-to-date"),
            df: {
                fieldtype: "Date",
                default: this.filters.to_date,
                input_class: "input-xs",
                change: () => {
                    this.filters.to_date = this.controls.to_date.get_value();
                    this.load_data();
                }
            },
            render_input: true,
        });

        // 4. Branch Link
        this.controls.branch = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-branch"),
            df: {
                fieldtype: "Link",
                options: "Branch",
                placeholder: __("Select Branch"),
                input_class: "input-xs",
                change: () => {
                    this.filters.branch = this.controls.branch.get_value() || "";
                    this.load_data();
                }
            },
            render_input: true,
        });

        // 5. Sales Order Link
        this.controls.sales_order = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-sales-order"),
            df: {
                fieldtype: "Link",
                options: "Sales Order",
                placeholder: __("Select Sales Order"),
                get_query: () => {
                    const filters = { docstatus: 1 };
                    if (this.filters.branch) filters.branch = this.filters.branch;
                    if (this.filters.customer) filters.customer = this.filters.customer;
                    return { filters: filters };
                },
                input_class: "input-xs",
                change: () => {
                    this.filters.sales_order = this.controls.sales_order.get_value() || "";
                    this.load_data();
                }
            },
            render_input: true,
        });

        // 6. Customer Link
        this.controls.customer = frappe.ui.form.make_control({
            parent: body.find(".sopt-control-customer"),
            df: {
                fieldtype: "Link",
                options: "Customer",
                placeholder: __("Select Customer"),
                input_class: "input-xs",
                change: () => {
                    this.filters.customer = this.controls.customer.get_value() || "";
                    this.load_data();
                }
            },
            render_input: true,
        });
    }

    bind_events() {
        const body = $(this.page.body);

        // Header actions
        body.find(".sopt-btn-reload").on("click", () => this.load_data());
        body.find(".sopt-btn-export").on("click", () => this.export_data());

        // Reset filters button
        body.find(".sopt-btn-reset").on("click", () => {
            this.filters = {
                period: "Last Month",
                branch: "",
                sales_order: "",
                customer: "",
            };
            const dates = this.resolve_preset(this.filters.period);
            this.filters.from_date = dates.from_date;
            this.filters.to_date = dates.to_date;

            this.controls.period.set_value(this.filters.period);
            this.controls.from_date.set_value(this.filters.from_date);
            this.controls.to_date.set_value(this.filters.to_date);
            this.controls.branch.set_value("");
            this.controls.sales_order.set_value("");
            this.controls.customer.set_value("");
            this.search_query = "";
            body.find('[data-role="table-search"]').val("");
            this.load_data();
        });

        // Debounced search
        let search_timeout = null;
        body.find('[data-role="table-search"]').on("input", (e) => {
            clearTimeout(search_timeout);
            search_timeout = setTimeout(() => {
                this.search_query = (e.target.value || "").trim().toLowerCase();
                this.current_page = 1;
                this.render_table();
            }, 250);
        });

        // Page size change
        body.find('[data-role="page-size-select"]').on("change", (e) => {
            this.page_size = parseInt(e.target.value, 10);
            this.current_page = 1;
            this.render_table();
        });

        // Pagination buttons
        body.find('[data-role="prev-page"]').on("click", () => {
            if (this.current_page > 1) {
                this.current_page -= 1;
                this.render_table();
            }
        });

        body.find('[data-role="next-page"]').on("click", () => {
            if (this.current_page < this.get_total_pages()) {
                this.current_page += 1;
                this.render_table();
            }
        });

        // Column sort
        body.find(".sopt-data-table thead th.sortable").on("click", (e) => {
            const th = $(e.currentTarget);
            const sort_field = th.data("sort");
            if (!sort_field) return;

            if (this.sort_field === sort_field) {
                this.sort_order = this.sort_order === "asc" ? "desc" : "asc";
            } else {
                this.sort_field = sort_field;
                this.sort_order = "desc";
            }

            this.update_sort_headers();
            this.render_table();
        });
    }

    resolve_preset(period) {
        const todayDate = frappe.datetime.now_date ? frappe.datetime.str_to_obj(frappe.datetime.now_date()) : new Date();
        const fmt = (d) => frappe.datetime.obj_to_str(d);
        const today = fmt(todayDate);

        switch (period) {
            case "Today":
                return { from_date: today, to_date: today };
            case "Last Week": {
                const currentDay = todayDate.getDay();
                const diffToLastMonday = (currentDay === 0 ? 6 : currentDay - 1) + 7;
                const start = new Date(todayDate);
                start.setDate(todayDate.getDate() - diffToLastMonday);
                const end = new Date(start);
                end.setDate(start.getDate() + 6);
                return { from_date: fmt(start), to_date: fmt(end) };
            }
            case "Last Month": {
                const first = new Date(todayDate.getFullYear(), todayDate.getMonth() - 1, 1);
                const last = new Date(todayDate.getFullYear(), todayDate.getMonth(), 0);
                return { from_date: fmt(first), to_date: fmt(last) };
            }
            case "Last Quarter": {
                const currentQuarter = Math.floor(todayDate.getMonth() / 3);
                const lastQuarterStartMonth = (currentQuarter - 1) * 3;
                const year = lastQuarterStartMonth < 0 ? todayDate.getFullYear() - 1 : todayDate.getFullYear();
                const startMonth = (lastQuarterStartMonth + 12) % 12;
                const first = new Date(year, startMonth, 1);
                const last = new Date(year, startMonth + 3, 0);
                return { from_date: fmt(first), to_date: fmt(last) };
            }
            default:
                return { from_date: today, to_date: today };
        }
    }

    load_data() {
        const body = $(this.page.body);
        const btnReload = body.find(".sopt-btn-reload i");
        btnReload.addClass("fa-spin");

        frappe.call({
            method: "generate_item.generate_item.page.sales_order_time_rev.sales_order_time_rev.get_dashboard_data",
            args: {
                period: this.filters.period,
                from_date: this.filters.from_date,
                to_date: this.filters.to_date,
                branch: this.filters.branch,
                sales_order: this.filters.sales_order,
                customer: this.filters.customer,
            },
            callback: (r) => {
                btnReload.removeClass("fa-spin");
                if (r && r.message) {
                    this.raw_rows = r.message.rows || [];
                    this.summary = r.message.summary || {};
                    this.render_cards();
                    this.current_page = 1;
                    this.update_sort_headers();
                    this.render_table();
                } else {
                    this.raw_rows = [];
                    this.summary = {};
                    this.render_cards();
                    this.render_table();
                }
            },
            error: () => {
                btnReload.removeClass("fa-spin");
                frappe.msgprint({
                    title: __("Error"),
                    message: __("Failed to load Sales Order phase time data."),
                    indicator: "red"
                });
            }
        });
    }

    render_cards() {
        const cards_container = $(this.page.body).find('[data-role="cards-container"]');
        const cards = (this.summary && this.summary.cards) || [];

        if (!cards.length) {
            cards_container.html(this.get_skeleton_cards_html());
            return;
        }

        const phase_meta = [
            { cls: "phase-1", tag: "STAGE 1", icon: "fa-check-square-o" },
            { cls: "phase-2", tag: "STAGE 2", icon: "fa-sitemap" },
            { cls: "phase-3", tag: "STAGE 3", icon: "fa-file-text-o" },
            { cls: "phase-4", tag: "STAGE 4", icon: "fa-shopping-cart" },
            { cls: "phase-5", tag: "STAGE 5", icon: "fa-truck" },
            { cls: "phase-overall", tag: "STAGE 6", icon: "fa-cogs" },
        ];

        const html = cards.map((card, idx) => {
            const meta = phase_meta[idx] || { cls: "phase-1", tag: `STAGE ${idx+1}`, icon: "fa-clock-o" };
            const val = card.avg_weeks !== null && card.avg_weeks !== undefined ? card.avg_weeks : null;
            const days_val = card.avg_days !== null && card.avg_days !== undefined ? card.avg_days : null;
            const has_val = val !== null && val !== undefined;
            const val_str = has_val ? Number(val).toFixed(2) : `<span class="sopt-dash">—</span>`;
            const unit_str = has_val ? "Weeks avg" : "";
            const days_str = has_val && days_val !== null ? `${Number(days_val).toFixed(1)} days avg` : "";

            const badge_html = card.delta
                ? `<span class="sopt-card-subbadge">${card.delta}</span>`
                : (card.count > 0 ? `<span class="sopt-card-count"><i class="fa fa-check text-success"></i> ${card.count} of ${card.total} orders</span>` : `<span class="text-muted">— no data</span>`);

            return `
                <div class="sopt-card ${meta.cls}">
                    <div class="sopt-card-top">
                        <span class="sopt-card-tag">${meta.tag}</span>
                        <div class="sopt-card-icon-circle">
                            <i class="fa ${meta.icon}"></i>
                        </div>
                    </div>
                    <div class="sopt-card-title">${card.label}</div>
                    <div class="sopt-card-body">
                        <span class="sopt-card-num">${val_str}</span>
                        <div class="sopt-card-units-group">
                            ${unit_str ? `<span class="sopt-card-unit">${unit_str}</span>` : ""}
                            ${days_str ? `<span class="sopt-card-days-pill">${days_str}</span>` : ""}
                        </div>
                    </div>
                    <div class="sopt-card-footer">
                        ${badge_html}
                    </div>
                </div>
            `;
        }).join("");

        cards_container.html(html);
    }

    get_skeleton_cards_html() {
        const labels = [
            __("SO Creation → SO Approved"),
            __("SO Approval → Last BOM Submitted"),
            __("Last BOM Submitted → Last Material Request Created on"),
            __("Last Material Request Submitted → Last Purchase Order Created on"),
            __("Last PO Approved → Last PR Submitted on"),
            __("Sales Order Created on → Work Order Submitted"),
        ];

        const phase_meta = [
            { cls: "phase-1", tag: "STAGE 1", icon: "fa-check-square-o" },
            { cls: "phase-2", tag: "STAGE 2", icon: "fa-sitemap" },
            { cls: "phase-3", tag: "STAGE 3", icon: "fa-file-text-o" },
            { cls: "phase-4", tag: "STAGE 4", icon: "fa-shopping-cart" },
            { cls: "phase-5", tag: "STAGE 5", icon: "fa-truck" },
            { cls: "phase-overall", tag: "STAGE 6", icon: "fa-cogs" },
        ];

        return labels.map((label, idx) => {
            const meta = phase_meta[idx] || { cls: "phase-1", tag: "STAGE", icon: "fa-clock-o" };
            return `
                <div class="sopt-card ${meta.cls}">
                    <div class="sopt-card-top">
                        <span class="sopt-card-tag">${meta.tag}</span>
                        <div class="sopt-card-icon-circle">
                            <i class="fa ${meta.icon}"></i>
                        </div>
                    </div>
                    <div class="sopt-card-title">${label}</div>
                    <div class="sopt-card-body">
                        <span class="sopt-card-num"><span class="sopt-dash">—</span></span>
                    </div>
                    <div class="sopt-card-footer">
                        <span class="text-muted">${__("Loading...")}</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    get_filtered_rows() {
        let rows = this.raw_rows || [];

        if (this.search_query) {
            const q = this.search_query;
            rows = rows.filter((r) => {
                return (
                    (r.sales_order && r.sales_order.toLowerCase().includes(q)) ||
                    (r.customer && r.customer.toLowerCase().includes(q)) ||
                    (r.customer_name && r.customer_name.toLowerCase().includes(q)) ||
                    (r.branch && r.branch.toLowerCase().includes(q))
                );
            });
        }

        // Sorting
        const field = this.sort_field;
        const order = this.sort_order === "asc" ? 1 : -1;

        rows.sort((a, b) => {
            let va = a[field];
            let vb = b[field];

            // Always place nulls at bottom
            if (va === null || va === undefined || va === "") return 1;
            if (vb === null || vb === undefined || vb === "") return -1;

            if (typeof va === "number" && typeof vb === "number") {
                return (va - vb) * order;
            }

            return String(va).localeCompare(String(vb)) * order;
        });

        return rows;
    }

    get_total_pages() {
        const total = this.get_filtered_rows().length;
        if (this.page_size >= total || this.page_size >= 999999) return 1;
        return Math.ceil(total / this.page_size);
    }

    update_sort_headers() {
        const ths = $(this.page.body).find(".sopt-data-table thead th.sortable");
        ths.removeClass("sorted").find(".sort-icon").text("");

        const current_th = ths.filter(`[data-sort="${this.sort_field}"]`);
        if (current_th.length) {
            current_th.addClass("sorted");
            current_th.find(".sort-icon").text(this.sort_order === "asc" ? " ▲" : " ▼");
        }
    }

    render_table() {
        const body = $(this.page.body);
        const filtered = this.get_filtered_rows();
        const total = filtered.length;

        body.find('[data-role="record-count"]').text(`${total} ${__("Orders")}`);

        if (total === 0) {
            body.find('[data-role="table-body"]').html(`
                <tr>
                    <td colspan="9" class="sopt-empty-box">
                        <i class="fa fa-folder-open-o"></i>
                        <h4>${__("No Sales Orders Found")}</h4>
                        <div>${__("Try changing your period preset, adjusting filters, or clearing the search box.")}</div>
                    </td>
                </tr>
            `);
            this.update_pagination(0, 0, 0);
            return;
        }

        // Slice pagination
        const total_pages = this.get_total_pages();
        if (this.current_page > total_pages) this.current_page = total_pages;
        if (this.current_page < 1) this.current_page = 1;

        const start_idx = (this.current_page - 1) * this.page_size;
        const end_idx = Math.min(start_idx + this.page_size, total);
        const page_rows = filtered.slice(start_idx, end_idx);

        const html = page_rows.map((r) => {
            const cust_display = r.customer_name || r.customer || "";
            const initials = this.get_initials(cust_display);

            return `
                <tr>
                    <!-- Sticky Sales Order Column -->
                    <td class="sticky-col">
                        <div class="sopt-so-cell">
                            <a href="/app/sales-order/${frappe.utils.escape_html(r.sales_order)}" class="sopt-so-link" target="_blank">
                                ${frappe.utils.escape_html(r.sales_order)}
                                <i class="fa fa-external-link" style="font-size: 10px; opacity: 0.6;"></i>
                            </a>
                            ${r.branch ? `<span class="sopt-branch-pill">${frappe.utils.escape_html(r.branch)}</span>` : ""}
                        </div>
                    </td>

                    <!-- Customer -->
                    <td>
                        <div class="sopt-cust-cell" title="${frappe.utils.escape_html(cust_display)}">
                            <div class="sopt-cust-avatar">${initials}</div>
                            <span class="sopt-cust-name">${frappe.utils.escape_html(cust_display)}</span>
                        </div>
                    </td>

                    <!-- SO Date -->
                    <td class="text-nowrap">${r.so_date || `<span class="sopt-dash">—</span>`}</td>

                    <!-- 1. SO Creation → SO Approved -->
                    <td class="col-border-group text-nowrap">${this.format_duration_pill(r.dur_so_cre_to_so_app, r.days_so_cre_to_so_app)}</td>

                    <!-- 2. SO Approval → Last BOM Submitted -->
                    <td class="text-nowrap">${this.format_duration_pill(r.dur_so_app_to_last_bom_sub, r.days_so_app_to_last_bom_sub)}</td>

                    <!-- 3. Last BOM Submitted → Last Material Request Created on -->
                    <td class="text-nowrap">${this.format_duration_pill(r.dur_bom_sub_to_mr_cre, r.days_bom_sub_to_mr_cre)}</td>

                    <!-- 4. Last Material Request Submitted → Last Purchase Order Created on -->
                    <td class="text-nowrap">${this.format_duration_pill(r.dur_mr_sub_to_po_cre, r.days_mr_sub_to_po_cre)}</td>

                    <!-- 5. Last PO Approved → Last PR Submitted on -->
                    <td class="text-nowrap">${this.format_duration_pill(r.dur_po_app_to_last_pur_sub, r.days_po_app_to_last_pur_sub)}</td>

                    <!-- 6. Sales Order Created on → Work Order Submitted -->
                    <td class="text-nowrap">${this.format_duration_pill(r.dur_so_cre_to_wo_sub, r.days_so_cre_to_wo_sub)}</td>
                </tr>
            `;
        }).join("");

        body.find('[data-role="table-body"]').html(html);
        this.update_pagination(start_idx + 1, end_idx, total);
    }

    format_duration_pill(weeks, days) {
        if (weeks === null || weeks === undefined || isNaN(weeks)) {
            return `<span class="sopt-dash">—</span>`;
        }
        const w_str = Number(weeks).toFixed(2) + " wks";
        const d_count = days !== null && days !== undefined && !isNaN(days) ? days : Math.round(weeks * 7);
        const d_str = `(${d_count} ${Math.abs(d_count) === 1 ? "day" : "days"})`;
        const val_str = `${w_str} <span class="sopt-pill-days">${d_str}</span>`;
        let level = "moderate";
        if (weeks <= 1.0) {
            level = "fast";
        } else if (weeks > 4.0) {
            level = "extended";
        }
        return `<span class="sopt-dur-pill ${level}">${val_str}</span>`;
    }

    get_initials(name) {
        if (!name) return "SO";
        const parts = name.trim().split(/\s+/);
        if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    update_pagination(start, end, total) {
        const body = $(this.page.body);
        const total_pages = this.get_total_pages();

        body.find('[data-role="footer-info"]').text(
            total > 0
                ? `${__("Showing")} ${start}–${end} ${__("of")} ${total} ${__("Sales Orders")}`
                : __("Showing 0 to 0 of 0 records")
        );

        body.find('[data-role="page-indicator"]').text(
            `${__("Page")} ${total > 0 ? this.current_page : 0} ${__("of")} ${total_pages}`
        );

        body.find('[data-role="prev-page"]').prop("disabled", this.current_page <= 1);
        body.find('[data-role="next-page"]').prop("disabled", this.current_page >= total_pages || total === 0);
    }

    export_data() {
        const rows = this.get_filtered_rows();
        if (!rows.length) {
            frappe.msgprint(__("No data available to export."));
            return;
        }

        const headers = [
            "Sales Order",
            "Customer",
            "Branch",
            "SO Date",
            "SO Creation to SO Approved (Weeks & Days)",
            "SO Approval to Last BOM Submitted (Weeks & Days)",
            "Last BOM Submitted to Last Material Request Created on (Weeks & Days)",
            "Last Material Request Submitted to Last Purchase Order Created on (Weeks & Days)",
            "Last PO Approved to Last PR Submitted on (Weeks & Days)",
            "Sales Order Created on to Work Order Submitted (Weeks & Days)",
        ];

        const fmt_dur = (w, d) => {
            if (w === null || w === undefined || isNaN(w)) return "-";
            const d_count = d !== null && d !== undefined && !isNaN(d) ? d : Math.round(w * 7);
            return `${Number(w).toFixed(2)} weeks (${d_count} days)`;
        };

        const csv_rows = rows.map((r) => [
            r.sales_order,
            `"${(r.customer_name || r.customer || "").replace(/"/g, '""')}"`,
            r.branch || "",
            r.so_date || "",
            fmt_dur(r.dur_so_cre_to_so_app, r.days_so_cre_to_so_app),
            fmt_dur(r.dur_so_app_to_last_bom_sub, r.days_so_app_to_last_bom_sub),
            fmt_dur(r.dur_bom_sub_to_mr_cre, r.days_bom_sub_to_mr_cre),
            fmt_dur(r.dur_mr_sub_to_po_cre, r.days_mr_sub_to_po_cre),
            fmt_dur(r.dur_po_app_to_last_pur_sub, r.days_po_app_to_last_pur_sub),
            fmt_dur(r.dur_so_cre_to_wo_sub, r.days_so_cre_to_wo_sub),
        ]);

        let csv_content = headers.join(",") + "\n";
        csv_rows.forEach((rowArray) => {
            csv_content += rowArray.join(",") + "\n";
        });

        const blob = new Blob([csv_content], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        const filename = `sales_order_phase_time_${frappe.datetime.now_date()}.csv`;

        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}