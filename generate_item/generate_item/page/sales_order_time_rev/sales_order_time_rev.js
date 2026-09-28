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
        if (document.getElementById("sopt-styles")) return;
        const style = document.createElement("style");
        style.id = "sopt-styles";
        style.textContent = `
            .sopt-page-wrap { max-width: 1600px; margin: 0 auto; padding: 12px 16px 40px; color: var(--text-color, #1f272e); font-size: var(--text-sm, 13px); }
            .sopt-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
            .sopt-title { font-size: 22px; font-weight: 700; margin: 0 0 4px; color: var(--text-color, #1f272e); }
            .sopt-subtitle { font-size: 13px; color: var(--text-muted, #6b7280); }
            .sopt-header-actions { display: flex; gap: 8px; }
            .sopt-filter-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05)); padding: 16px; margin-bottom: 20px; }
            .sopt-filter-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
            .sopt-filter-title { font-weight: 600; font-size: 14px; color: var(--text-color, #1f272e); }
            .sopt-filter-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px 16px; align-items: end; }
            .sopt-filter-group { display: flex; flex-direction: column; gap: 4px; }
            .sopt-filter-label { font-size: 12px; font-weight: 500; color: var(--text-muted, #6b7280); }
            .sopt-filter-actions { display: flex; gap: 8px; margin-top: 14px; justify-content: flex-end; }
            .sopt-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 24px; }
            .sopt-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; padding: 14px 16px; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04)); display: flex; flex-direction: column; justify-content: space-between; min-height: 104px; position: relative; }
            .sopt-card-label { font-size: 12px; font-weight: 600; color: var(--text-muted, #6b7280); margin-bottom: 6px; line-height: 1.3; }
            .sopt-card-value { font-size: 26px; font-weight: 700; color: var(--text-color, #1f272e); line-height: 1.1; margin-bottom: 6px; }
            .sopt-card-footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-muted, #8d99a6); }
            .sopt-card-unit { font-weight: 500; }
            .sopt-card-delta { font-size: 11px; font-weight: 600; color: var(--primary, #171717); background: var(--control-bg, #f4f5f6); border-radius: 4px; padding: 2px 6px; }
            .sopt-card-count { font-size: 11px; color: var(--text-muted, #8d99a6); }
            .sopt-section { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px; box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05)); overflow: hidden; margin-bottom: 24px; }
            .sopt-section-head { padding: 14px 18px; border-bottom: 1px solid var(--border-color, #ebeff2); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
            .sopt-section-title-wrap { display: flex; flex-direction: column; gap: 2px; }
            .sopt-section-title { font-size: 16px; font-weight: 700; color: var(--text-color, #1f272e); margin: 0; }
            .sopt-section-subtitle { font-size: 12px; color: var(--text-muted, #6b7280); }
            .sopt-formula-bar { background: var(--control-bg, #f8f9fa); border-bottom: 1px solid var(--border-color, #ebeff2); padding: 8px 18px; font-size: 12px; color: var(--text-muted, #555); display: flex; align-items: center; gap: 8px; }
            .sopt-formula-tag { background: #e3f2fd; color: #1565c0; font-weight: 600; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
            .sopt-table-toolbar { padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; background: #fff; border-bottom: 1px solid var(--border-color, #ebeff2); }
            .sopt-search-box { position: relative; width: 280px; }
            .sopt-search-box input { width: 100%; height: 32px; padding: 4px 10px 4px 30px; font-size: 12px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; outline: none; }
            .sopt-search-box input:focus { border-color: var(--primary, #171717); }
            .sopt-search-icon { position: absolute; left: 10px; top: 8px; font-size: 12px; color: var(--text-muted, #8d99a6); }
            .sopt-table-wrap { overflow-x: auto; width: 100%; max-height: 640px; position: relative; }
            .sopt-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 12px; text-align: left; }
            .sopt-table thead th { background: var(--control-bg, #f8f9fa); color: var(--text-muted, #525f6e); font-weight: 600; padding: 10px 12px; border-bottom: 1px solid var(--border-color, #d1d8dd); border-right: 1px solid var(--border-color, #f0f0f0); white-space: nowrap; position: sticky; top: 0; z-index: 2; user-select: none; }
            .sopt-table thead th.sortable { cursor: pointer; }
            .sopt-table thead th.sortable:hover { background: #ebeff2; color: var(--text-color, #1f272e); }
            .sopt-table thead th.sortable .sort-icon { font-size: 10px; margin-left: 4px; opacity: 0.6; }
            .sopt-table thead th.sortable.sorted .sort-icon { opacity: 1; color: var(--primary, #171717); }
            .sopt-table thead tr.sub-header th { font-size: 11px; background: #f0f4f7; padding: 6px 12px; font-weight: 600; text-align: center; }
            .sopt-table tbody tr { transition: background 0.15s ease; }
            .sopt-table tbody tr:hover { background: #f7f9fa; }
            .sopt-table tbody td { padding: 9px 12px; border-bottom: 1px solid var(--border-color, #f0f4f7); border-right: 1px solid var(--border-color, #f9f9f9); vertical-align: middle; }
            .sopt-table th.sticky-col, .sopt-table td.sticky-col { position: sticky; left: 0; background: #fff; z-index: 1; box-shadow: 2px 0 4px rgba(0,0,0,0.04); }
            .sopt-table thead th.sticky-col { z-index: 3; background: var(--control-bg, #f8f9fa); }
            .sopt-table tbody tr:hover td.sticky-col { background: #f7f9fa; }
            .sopt-duration-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 58px; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; background: #eef2ff; color: #3730a3; border: 1px solid #c7d2fe; white-space: nowrap; }
            .sopt-duration-badge.overall { background: #ecfdf5; color: #065f46; border-color: #a7f3d0; font-weight: 700; }
            .sopt-muted-dash { color: #adb5bd; font-weight: 500; font-size: 14px; text-align: center; display: inline-block; width: 100%; }
            .sopt-so-link { font-weight: 600; color: var(--primary, #171717); text-decoration: none; }
            .sopt-so-link:hover { text-decoration: underline; color: #000; }
            .sopt-doc-sublink { font-size: 11px; color: var(--text-muted, #6b7280); text-decoration: none; display: inline-block; margin-top: 2px; }
            .sopt-doc-sublink:hover { text-decoration: underline; color: var(--primary, #171717); }
            .sopt-pagination { padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; background: #fff; border-top: 1px solid var(--border-color, #ebeff2); flex-wrap: wrap; gap: 8px; font-size: 12px; }
            .sopt-loading-wrap { position: relative; opacity: 0.6; pointer-events: none; }
            .sopt-empty-state { text-align: center; padding: 48px 16px; color: var(--text-muted, #8d99a6); }
            .sopt-empty-state i { font-size: 32px; margin-bottom: 8px; opacity: 0.4; }
            .sopt-empty-title { font-weight: 600; font-size: 14px; color: var(--text-color, #1f272e); margin-bottom: 4px; }
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
                <!-- Top Filters Card -->
                <div class="sopt-filter-card">
                    <div class="sopt-filter-header">
                        <div class="sopt-filter-title"><i class="fa fa-filter mr-1"></i> ${__("Filters & Parameters")}</div>
                        <div>
                            <button class="btn btn-xs btn-default sopt-btn-reset"><i class="fa fa-undo"></i> ${__("Reset")}</button>
                        </div>
                    </div>
                    <div class="sopt-filter-grid">
                        <div class="sopt-filter-group" data-filter="period">
                            <label class="sopt-filter-label">${__("Period")}</label>
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

                <!-- Number Cards -->
                <div class="sopt-cards-grid" data-role="cards-container">
                    ${this.get_skeleton_cards_html()}
                </div>

                <!-- Sales Order Phase Timeline Section -->
                <div class="sopt-section">
                    <div class="sopt-section-head">
                        <div class="sopt-section-title-wrap">
                            <h3 class="sopt-section-title">${__("Sales Order Phase Timeline")}</h3>
                            <span class="sopt-section-subtitle">${__("One row per Sales Order; phase duration is calculated from document timestamps.")}</span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge badge-light" data-role="record-count">0 ${__("Sales Orders")}</span>
                        </div>
                    </div>

                    <div class="sopt-formula-bar">
                        <span class="sopt-formula-tag">${__("Calculation Rule")}</span>
                        <span>${__("Duration = later milestone timestamp − earlier milestone timestamp. If a required document does not exist, display '—' and exclude that row from that phase's average.")}</span>
                    </div>

                    <div class="sopt-table-toolbar">
                        <div class="sopt-search-box">
                            <i class="fa fa-search sopt-search-icon"></i>
                            <input type="text" placeholder="${__("Search Sales Order, Customer, BOM, PO, WO...")}" data-role="table-search">
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-muted small">${__("Rows per page:")}</span>
                            <select class="form-control input-xs" style="width: auto; height: 30px;" data-role="page-size-select">
                                <option value="10">10</option>
                                <option value="25" selected>25</option>
                                <option value="50">50</option>
                                <option value="100">100</option>
                                <option value="999999">${__("All")}</option>
                            </select>
                        </div>
                    </div>

                    <div class="sopt-table-wrap">
                        <table class="sopt-table">
                            <thead>
                                <tr>
                                    <th rowspan="2" class="sticky-col sortable" data-sort="sales_order">${__("Sales Order")} <span class="sort-icon"></span></th>
                                    <th rowspan="2" class="sortable" data-sort="customer_name">${__("Customer")} <span class="sort-icon"></span></th>
                                    <th rowspan="2" class="sortable" data-sort="so_date_raw">${__("SO Date")} <span class="sort-icon"></span></th>
                                    <th rowspan="2" class="sortable" data-sort="so_approval_date_raw">${__("SO Approval (Submitted)")} <span class="sort-icon"></span></th>
                                    <th colspan="5" style="text-align: center; border-left: 2px solid var(--border-color, #d1d8dd); border-right: 2px solid var(--border-color, #d1d8dd);">${__("Milestone Dates & Document Links")}</th>
                                    <th colspan="6" style="text-align: center;">${__("Phase Durations (Days)")}</th>
                                </tr>
                                <tr class="sub-header">
                                    <!-- Milestones -->
                                    <th class="sortable" data-sort="last_bom_created_date_raw">${__("Last BOM Created")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="last_bom_submitted_date_raw">${__("Last BOM Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="last_po_submitted_date_raw">${__("Last PO Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="last_pr_submitted_date_raw">${__("Last PR Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="last_wo_submitted_date_raw">${__("Last WO Submitted")} <span class="sort-icon"></span></th>

                                    <!-- Durations -->
                                    <th class="sortable" data-sort="dur_so_to_bom_created">${__("SO Approval → Last BOM Created")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="dur_bom_created_to_submitted">${__("BOM Created → BOM Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="dur_bom_to_po_submitted">${__("BOM Submitted → PO Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="dur_po_to_pr_submitted">${__("PO Submitted → PR Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="dur_pr_to_wo_submitted">${__("PR Submitted → WO Submitted")} <span class="sort-icon"></span></th>
                                    <th class="sortable" data-sort="dur_overall">${__("Sales Order → Last WO Submitted")} <span class="sort-icon"></span></th>
                                </tr>
                            </thead>
                            <tbody data-role="table-body">
                                <tr>
                                    <td colspan="15" class="sopt-empty-state">
                                        <i class="fa fa-spinner fa-spin"></i>
                                        <div class="sopt-empty-title">${__("Loading Sales Orders...")}</div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="sopt-pagination">
                        <div class="text-muted" data-role="footer-info">
                            ${__("Showing 0 to 0 of 0 records")}
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <button class="btn btn-default btn-xs" data-role="prev-page" disabled><i class="fa fa-chevron-left"></i> ${__("Previous")}</button>
                            <span class="small font-weight-bold" data-role="page-indicator">${__("Page 1 of 1")}</span>
                            <button class="btn btn-default btn-xs" data-role="next-page" disabled>${__("Next")} <i class="fa fa-chevron-right"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        body.html(html);
    }

    init_filter_controls() {
        const body = $(this.page.body);

        // 1. Period Select Control
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

        // 2. From Date Control
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

        // 3. To Date Control
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

        // 4. Branch Link Control
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

        // 5. Sales Order Link Control
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

        // 6. Customer Link Control
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
        body.find(".sopt-table thead th.sortable").on("click", (e) => {
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
        body.find(".sopt-section").addClass("sopt-loading-wrap");

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
                body.find(".sopt-section").removeClass("sopt-loading-wrap");
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
                body.find(".sopt-section").removeClass("sopt-loading-wrap");
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

        const html = cards.map((card) => {
            const val_str = card.avg_days !== null && card.avg_days !== undefined
                ? `${card.avg_days} <span style="font-size: 14px; font-weight: 500; color: var(--text-muted, #6c757d);">${Math.abs(card.avg_days - 1.0) < 0.001 ? 'Day' : 'Days'}</span>`
                : `<span class="sopt-muted-dash">—</span>`;
            
            const badge_html = card.delta
                ? `<span class="sopt-card-delta">${card.delta}</span>`
                : (card.count > 0 ? `<span class="sopt-card-count">${card.count} of ${card.total} orders</span>` : ``);

            return `
                <div class="sopt-card">
                    <div class="sopt-card-label">${card.label}</div>
                    <div class="sopt-card-value">${val_str}</div>
                    <div class="sopt-card-footer">
                        <span class="sopt-card-unit">${card.avg_days !== null ? card.unit : __("no data")}</span>
                        ${badge_html}
                    </div>
                </div>
            `;
        }).join("");

        cards_container.html(html);
    }

    get_skeleton_cards_html() {
        const labels = [
            __("SO Approval → Last BOM Created"),
            __("Last BOM Created → Last BOM Submitted"),
            __("Last BOM Submitted → Last PO Submitted"),
            __("Last PO Submitted → Last Purchase Receipt Submitted"),
            __("Last Purchase Receipt → Last Work Order Submitted"),
            __("Sales Order → Last Work Order Submitted"),
        ];

        return labels.map((label) => `
            <div class="sopt-card">
                <div class="sopt-card-label">${label}</div>
                <div class="sopt-card-value text-muted">—</div>
                <div class="sopt-card-footer">
                    <span class="sopt-card-unit">${__("days average")}</span>
                </div>
            </div>
        `).join("");
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
                    (r.branch && r.branch.toLowerCase().includes(q)) ||
                    (r.last_bom_created_name && r.last_bom_created_name.toLowerCase().includes(q)) ||
                    (r.last_bom_submitted_name && r.last_bom_submitted_name.toLowerCase().includes(q)) ||
                    (r.last_po_submitted_name && r.last_po_submitted_name.toLowerCase().includes(q)) ||
                    (r.last_pr_submitted_name && r.last_pr_submitted_name.toLowerCase().includes(q)) ||
                    (r.last_wo_submitted_name && r.last_wo_submitted_name.toLowerCase().includes(q))
                );
            });
        }

        // Sorting
        const field = this.sort_field;
        const order = this.sort_order === "asc" ? 1 : -1;

        rows.sort((a, b) => {
            let va = a[field];
            let vb = b[field];

            // Handle nulls: always place null at the bottom
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
        const ths = $(this.page.body).find(".sopt-table thead th");
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

        body.find('[data-role="record-count"]').text(`${total} ${__("Sales Orders")}`);

        if (total === 0) {
            body.find('[data-role="table-body"]').html(`
                <tr>
                    <td colspan="15" class="sopt-empty-state">
                        <i class="fa fa-folder-open-o"></i>
                        <div class="sopt-empty-title">${__("No Sales Orders Found")}</div>
                        <div>${__("Try adjusting your filters, period, or search keywords.")}</div>
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
            return `
                <tr>
                    <td class="sticky-col">
                        <a href="/app/sales-order/${frappe.utils.escape_html(r.sales_order)}" class="sopt-so-link" target="_blank">
                            ${frappe.utils.escape_html(r.sales_order)}
                        </a>
                    </td>
                    <td>
                        <span title="${frappe.utils.escape_html(r.customer_name || r.customer)}">
                            ${frappe.utils.escape_html(r.customer_name || r.customer)}
                        </span>
                    </td>
                    <td class="text-nowrap">${r.so_date || `<span class="sopt-muted-dash">—</span>`}</td>
                    <td class="text-nowrap">${r.so_approval_date || `<span class="sopt-muted-dash">—</span>`}</td>

                    <!-- Milestone Dates + Clickable Links -->
                    <td class="text-nowrap">
                        ${this.format_milestone_cell(r.last_bom_created_date, r.last_bom_created_name, "bom")}
                    </td>
                    <td class="text-nowrap">
                        ${this.format_milestone_cell(r.last_bom_submitted_date, r.last_bom_submitted_name, "bom")}
                    </td>
                    <td class="text-nowrap">
                        ${this.format_milestone_cell(r.last_po_submitted_date, r.last_po_submitted_name, "purchase-order")}
                    </td>
                    <td class="text-nowrap">
                        ${this.format_milestone_cell(r.last_pr_submitted_date, r.last_pr_submitted_name, "purchase-receipt")}
                    </td>
                    <td class="text-nowrap">
                        ${this.format_milestone_cell(r.last_wo_submitted_date, r.last_wo_submitted_name, "work-order")}
                    </td>

                    <!-- Phase Durations -->
                    <td>${this.format_duration_cell(r.dur_so_to_bom_created)}</td>
                    <td>${this.format_duration_cell(r.dur_bom_created_to_submitted)}</td>
                    <td>${this.format_duration_cell(r.dur_bom_to_po_submitted)}</td>
                    <td>${this.format_duration_cell(r.dur_po_to_pr_submitted)}</td>
                    <td>${this.format_duration_cell(r.dur_pr_to_wo_submitted)}</td>
                    <td>${this.format_duration_cell(r.dur_overall, true)}</td>
                </tr>
            `;
        }).join("");

        body.find('[data-role="table-body"]').html(html);
        this.update_pagination(start_idx + 1, end_idx, total);
    }

    format_milestone_cell(date_str, doc_name, doctype_route) {
        if (!date_str) {
            return `<span class="sopt-muted-dash">—</span>`;
        }
        let link_html = "";
        if (doc_name) {
            link_html = `<br><a href="/app/${doctype_route}/${frappe.utils.escape_html(doc_name)}" class="sopt-doc-sublink" target="_blank" title="${frappe.utils.escape_html(doc_name)}">${frappe.utils.escape_html(doc_name)}</a>`;
        }
        return `<span>${date_str}</span>${link_html}`;
    }

    format_duration_cell(duration, is_overall = false) {
        if (duration === null || duration === undefined) {
            return `<span class="sopt-muted-dash">—</span>`;
        }
        const unit_text = Math.abs(duration - 1.0) < 0.001 ? "Day" : "Days";
        const cls = is_overall ? "sopt-duration-badge overall" : "sopt-duration-badge";
        return `<span class="${cls}">${duration} ${unit_text}</span>`;
    }

    update_pagination(start, end, total) {
        const body = $(this.page.body);
        const total_pages = this.get_total_pages();

        body.find('[data-role="footer-info"]').text(
            total > 0
                ? `${__("Showing")} ${start} ${__("to")} ${end} ${__("of")} ${total} ${__("records")}`
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
            "SO Approval Date",
            "Last BOM Created Date",
            "Last BOM Created Doc",
            "Last BOM Submitted Date",
            "Last BOM Submitted Doc",
            "Last PO Submitted Date",
            "Last PO Submitted Doc",
            "Last PR Submitted Date",
            "Last PR Submitted Doc",
            "Last WO Submitted Date",
            "Last WO Submitted Doc",
            "SO Approval to Last BOM Created (Days)",
            "BOM Created to BOM Submitted (Days)",
            "BOM Submitted to PO Submitted (Days)",
            "PO Submitted to PR Submitted (Days)",
            "PR Submitted to WO Submitted (Days)",
            "Sales Order to Last WO Submitted Overall (Days)",
        ];

        const csv_rows = rows.map((r) => [
            r.sales_order,
            `"${(r.customer_name || r.customer || "").replace(/"/g, '""')}"`,
            r.branch || "",
            r.so_date || "",
            r.so_approval_date || "",
            r.last_bom_created_date || "",
            r.last_bom_created_name || "",
            r.last_bom_submitted_date || "",
            r.last_bom_submitted_name || "",
            r.last_po_submitted_date || "",
            r.last_po_submitted_name || "",
            r.last_pr_submitted_date || "",
            r.last_pr_submitted_name || "",
            r.last_wo_submitted_date || "",
            r.last_wo_submitted_name || "",
            r.dur_so_to_bom_created !== null ? r.dur_so_to_bom_created : "",
            r.dur_bom_created_to_submitted !== null ? r.dur_bom_created_to_submitted : "",
            r.dur_bom_to_po_submitted !== null ? r.dur_bom_to_po_submitted : "",
            r.dur_po_to_pr_submitted !== null ? r.dur_po_to_pr_submitted : "",
            r.dur_pr_to_wo_submitted !== null ? r.dur_pr_to_wo_submitted : "",
            r.dur_overall !== null ? r.dur_overall : "",
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