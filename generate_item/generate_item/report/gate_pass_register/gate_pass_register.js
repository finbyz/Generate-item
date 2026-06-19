// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Gate Pass Register"] = {

    /* ───────────────────────────────────────────────────────────────────────
       FILTERS
    ─────────────────────────────────────────────────────────────────────── */
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 0,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0,
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            reqd: 0,
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Select",
            options: "\nSupplier\nCustomer",
            on_change: function () {
                frappe.query_report.set_filter_value("party_name", "");
                let party_type = frappe.query_report.get_filter_value("party_type");
                let party_filter = frappe.query_report.get_filter("party_name");
                if (party_type === "Supplier") {
                    party_filter.df.options = "Supplier";
                } else if (party_type === "Customer") {
                    party_filter.df.options = "Customer";
                }
                party_filter.refresh();
            }
        },
        {
            fieldname: "party_name",
            label: __("Party Name"),
            fieldtype: "Link",
            options: "Supplier"  // default
        },
        {
            fieldname: "gate_pass_outward",
            label: __("Gate Pass Outward"),
            fieldtype: "Link",
            options: "Gate Pass Outward",
            reqd: 0,
        },
        {
            fieldname: "returnable",
            label: __("Returnable"),
            fieldtype: "Select",
            options: "\nYes\nNo",
            reqd: 0,
        },
        {
            fieldname: "sub_component",
            label: __("Sub Component"),
            fieldtype: "Link",
            options: "Gatepass Component",
            reqd: 0,
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nOpen\nPartially Received\nCompleted\nClosed\nCancelled",
            reqd: 0,
        },
    ],

    /* ───────────────────────────────────────────────────────────────────────
       ONLOAD — initialize a single shared state object
    ─────────────────────────────────────────────────────────────────────── */
    onload(report) {
        const KEY = "Gate Pass Register";
        frappe.query_reports[KEY]._report = report;
        frappe.query_reports[KEY]._state = {
            view_mode: "detail",       // "detail" | "party"
            status_filter: "all",      // "all" | "Open" | "Partial" | "Closed" | "Non-Returnable" | "pending" | "critical"
            aging_bucket: "all",       // "all" | "0-30" | "30-60" | "60-90" | "90+"
            search_text: "",
            sort: { field: "pending_qty", dir: "desc" },
        };

        // Add Print and Export buttons to the report's page menu
      
        report.page.add_inner_button(__("Export Party Summary (CSV)"), () => gp_export_party_csv());
    },

    /* ───────────────────────────────────────────────────────────────────────
       FORMATTER
    ─────────────────────────────────────────────────────────────────────── */
    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (column.fieldname === "gp_status") {
            const cfg = {
                "Open": { bg: "#fff3cd", color: "#856404", border: "#ffc107" },
                "Partial": { bg: "#cce5ff", color: "#004085", border: "#b8daff" },
                "Closed": { bg: "#d4edda", color: "#155724", border: "#c3e6cb" },
                "Non-Returnable": { bg: "#f8d7da", color: "#721c24", border: "#f5c6cb" },
            };
            const s = cfg[data.gp_status] || { bg: "#f1f1f1", color: "#333", border: "#ccc" };
            return `<span style="
                background:${s.bg};color:${s.color};border:1px solid ${s.border};
                padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;
                display:inline-block;min-width:96px;text-align:center;letter-spacing:.3px;
            ">${data.gp_status || "—"}</span>`;
        }

        if (column.fieldname === "party_type") {
            if (data.party_type === "Customer") {
                return `<span style="background:#d1ecf1;color:#0c5460;border:1px solid #bee5eb;
                    padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">
                    👤 Customer</span>`;
            } else if (data.party_type === "Supplier") {
                return `<span style="background:#d4edda;color:#155724;border:1px solid #c3e6cb;
                    padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">
                    🏭 Supplier</span>`;
            }
        }

        if (column.fieldname === "returnable") {
            if (data.returnable === "Yes") {
                return `<span style="background:#d1ecf1;color:#0c5460;border:1px solid #bee5eb;
                    padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">
                    ↩ Yes</span>`;
            } else if (data.returnable === "No") {
                return `<span style="background:#f8d7da;color:#721c24;border:1px solid #f5c6cb;
                    padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">
                    ✕ No</span>`;
            }
        }

        if (column.fieldname === "component_status") {
            const cfg = {
                "In Service": { bg: "#d4edda", color: "#155724", icon: "✔" },
                "Sent Out": { bg: "#fff3cd", color: "#856404", icon: "📤" },
                "Scrapped": { bg: "#f8d7da", color: "#721c24", icon: "✖" },
                "Sold": { bg: "#e2d9f3", color: "#4a1ca8", icon: "💰" },
            };
            const s = cfg[data.component_status] || { bg: "#f1f1f1", color: "#555", icon: "?" };
            return `<span style="background:${s.bg};color:${s.color};
                padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                ${s.icon} ${data.component_status || "—"}</span>`;
        }

        if (column.fieldname === "docstatus") {
            const cfg = {
                "Draft": { bg: "#f1f1f1", color: "#555", icon: "📝" },
                "Submitted": { bg: "#d4edda", color: "#155724", icon: "✓" },
                "Cancelled": { bg: "#f8d7da", color: "#721c24", icon: "✕" },
            };
            const s = cfg[data.docstatus] || { bg: "#f1f1f1", color: "#555", icon: "?" };
            return `<span style="background:${s.bg};color:${s.color};
                padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                ${s.icon} ${data.docstatus || "—"}</span>`;
        }

        if (column.fieldname === "aging_days") {
            const days = parseInt(data.aging_days) || 0;
            let color = "#155724", bg = "#d4edda";
            if (days > 60) { color = "#721c24"; bg = "#f8d7da"; }
            else if (days > 30) { color = "#856404"; bg = "#fff3cd"; }
            return `<span style="background:${bg};color:${color};font-weight:600;
                padding:2px 9px;border-radius:12px;font-size:11px;">
                ${days}d</span>`;
        }

        if (column.fieldname === "outward_se_type" || column.fieldname === "inward_se_type") {
            if (!value || value === "—") return `<span style="color:#aaa;">—</span>`;
            return `<span style="background:#e2d9f3;color:#4a1ca8;border:1px solid #c9b8ef;
                padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                📦 ${data[column.fieldname]}</span>`;
        }

        if (column.fieldname === "outward_se_ref" || column.fieldname === "inward_se_ref") {
            const ref = data[column.fieldname];
            if (!ref || ref === "—") return `<span style="color:#aaa;">—</span>`;
            const links = ref.split(",").map(r => {
                const name = r.trim();
                return `<a href="/app/stock-entry/${name}" target="_blank"
                    style="color:#5e64ff;font-weight:600;text-decoration:none;">${name}</a>`;
            });
            return links.join(", ");
        }

        if (column.fieldname === "inward_refs") {
            const ref = data.inward_refs;
            if (!ref || ref === "—") return `<span style="color:#aaa;">—</span>`;
            const links = ref.split(",").map(r => {
                const name = r.trim();
                return `<a href="/app/gate-pass-inward/${name}" target="_blank"
                    style="color:#2ecc71;font-weight:600;text-decoration:none;">${name}</a>`;
            });
            return links.join("<br>");
        }

        if (column.fieldname === "billing_status") {
            if (data.billing_status === "Without Bill") {
                return `<span style="background:#fff3cd;color:#856404;border:1px solid #ffc107;
                    padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                    ⚠ Without Bill</span>`;
            } else if (data.billing_status === "With Bill") {
                return `<span style="background:#d4edda;color:#155724;border:1px solid #c3e6cb;
                    padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                    ✔ With Bill</span>`;
            }
        }

        if (column.fieldname === "pending_qty") {
            const qty = flt(data.pending_qty);
            if (qty > 0 && data.gp_status !== "Non-Returnable") {
                return `<span style="color:#dc3545;font-weight:700;">${qty}</span>`;
            }
            return `<span style="color:#28a745;font-weight:600;">${qty}</span>`;
        }

        if (column.fieldname === "outward_no") {
            return `<a href="/app/gate-pass-outward/${data.outward_no}" target="_blank"
                style="color:#5e64ff;font-weight:700;text-decoration:none;">
                ${data.outward_no}</a>`;
        }

        return value;
    },

    /* ───────────────────────────────────────────────────────────────────────
       GET DATATABLE OPTIONS
    ─────────────────────────────────────────────────────────────────────── */
    get_datatable_options(options) {
        return Object.assign(options, {
            checkboxColumn: true,
        });
    },

    /* ───────────────────────────────────────────────────────────────────────
       AFTER RENDER CALLBACK — fires after every report.refresh() / filter
       change / datatable.refresh(). This is the ONE place that rebuilds the
       toolbar; gp_render() below is the ONE place that decides what's visible.
    ─────────────────────────────────────────────────────────────────────── */
    after_datatable_render(datatable) {
        inject_kpi_and_toolbar(datatable);
    },
};

/* ─────────────────────────────────────────────────────────────────────────
   STATE HELPERS
───────────────────────────────────────────────────────────────────────── */
function gp_state() {
    return frappe.query_reports["Gate Pass Register"]._state;
}
function gp_report() {
    return frappe.query_reports["Gate Pass Register"]._report;
}

/* Apply status_filter + aging_bucket + search_text to the full dataset.
   This is the SINGLE source of truth for "what rows match right now" —
   used by both the Detail table and the Party Summary table, so they can
   never show different result sets. */
function gp_filtered_data() {
    const report = gp_report();
    const state = gp_state();
    let rows = (report && report.data) || [];

    // Status / KPI-card filter
    if (state.status_filter === "pending") {
        rows = rows.filter(r => flt(r.pending_qty) > 0);
    } else if (state.status_filter === "critical") {
        rows = rows.filter(r => parseInt(r.aging_days) > 60 && ["Open", "Partial"].includes(r.gp_status));
    } else if (state.status_filter !== "all") {
        rows = rows.filter(r => r.gp_status === state.status_filter);
    }

    // Aging bucket filter
    if (state.aging_bucket !== "all") {
        rows = rows.filter(r => {
            const d = parseInt(r.aging_days) || 0;
            if (state.aging_bucket === "0-30") return d <= 30;
            if (state.aging_bucket === "30-60") return d > 30 && d <= 60;
            if (state.aging_bucket === "60-90") return d > 60 && d <= 90;
            if (state.aging_bucket === "90+") return d > 90;
            return true;
        });
    }

    // Search text — matches party name, outward #, description, sub component
    if (state.search_text) {
        const q = state.search_text.toLowerCase();
        rows = rows.filter(r =>
            (r.party_name || "").toLowerCase().includes(q) ||
            (r.outward_no || "").toLowerCase().includes(q) ||
            (r.description || "").toLowerCase().includes(q) ||
            (r.sub_component || "").toLowerCase().includes(q) ||
            (r.vehicle_no || "").toLowerCase().includes(q) ||
            (r.lr_no || "").toLowerCase().includes(q)
        );
    }

    return rows;
}

/* THE single render function. Every user action (filter click, view toggle,
   search keystroke, sort click) ends by calling this — nothing else is
   allowed to touch visibility directly. This is what fixes the "both tables
   visible at once" bug: there is no code path that can update one table
   without this function also reconciling the other. */
function gp_render() {
    const report = gp_report();
    const state = gp_state();
    if (!report || !report.datatable) return;

    const filtered = gp_filtered_data();

    // Always keep the underlying datatable's row data in sync, even in
    // party view, so switching back to Detail is instant and correct.
    report.datatable.refresh(filtered, report.columns);

    const dtWrapper = $(report.datatable.wrapper);
    const summaryRoot = document.getElementById("gp-party-summary-root");

    if (state.view_mode === "party") {
        dtWrapper.css("display", "none");
        if (summaryRoot) {
            summaryRoot.style.display = "block";
            render_party_summary(filtered);
        }
    } else {
        dtWrapper.css("display", "");
        if (summaryRoot) {
            summaryRoot.style.display = "none";
        }
    }

    // Sync all toolbar control states (buttons/pills/search box) to match
    sync_toolbar_controls();
}

function sync_toolbar_controls() {
    const state = gp_state();
    document.querySelectorAll(".gp-filter-btn").forEach(el => {
        el.classList.toggle("active", el.dataset.status === state.status_filter);
    });
    document.querySelectorAll(".gp-view-btn").forEach(el => {
        el.classList.toggle("active", el.dataset.view === state.view_mode);
    });
    document.querySelectorAll(".gp-aging-btn").forEach(el => {
        el.classList.toggle("active", el.dataset.bucket === state.aging_bucket);
    });
    const searchInput = document.getElementById("gp-search-input");
    if (searchInput && searchInput.value !== state.search_text) {
        searchInput.value = state.search_text;
    }
}

/* ─────────────────────────────────────────────────────────────────────────
   HELPER — KPI Cards + Toolbar (filters, view toggle, search, aging)
───────────────────────────────────────────────────────────────────────── */
function inject_kpi_and_toolbar(datatable) {
    const report = gp_report();
    if (!report || !report.data || !report.data.length) return;

    const data = report.data;
    const state = gp_state();

    // ── Compute KPIs off the FULL dataset (not the filtered view) ─────────
    const totalSent = data.reduce((s, r) => s + flt(r.sent_qty), 0);
    const totalReceived = data.reduce((s, r) => s + flt(r.total_received), 0);
    const totalPending = data.reduce((s, r) => s + flt(r.pending_qty), 0);
    const totalAmount = data.reduce((s, r) => s + flt(r.total_amount), 0);
    const openCount = data.filter(r => r.gp_status === "Open").length;
    const partialCount = data.filter(r => r.gp_status === "Partial").length;
    const closedCount = data.filter(r => r.gp_status === "Closed").length;
    const nrCount = data.filter(r => r.gp_status === "Non-Returnable").length;
    const criticalCount = data.filter(
        r => parseInt(r.aging_days) > 60 && ["Open", "Partial"].includes(r.gp_status)
    ).length;

    // Aging bucket counts (off full dataset, non-returnable excluded from "aging" concept is up to you;
    // here we count all rows so buttons reflect literal day-range membership)
    const bucketCount = (lo, hi) => data.filter(r => {
        const d = parseInt(r.aging_days) || 0;
        return hi === null ? d > lo : (d > lo && d <= hi) || (lo === 0 && d <= hi);
    }).length;
    const b0_30 = data.filter(r => (parseInt(r.aging_days) || 0) <= 30).length;
    const b30_60 = data.filter(r => { const d = parseInt(r.aging_days) || 0; return d > 30 && d <= 60; }).length;
    const b60_90 = data.filter(r => { const d = parseInt(r.aging_days) || 0; return d > 60 && d <= 90; }).length;
    const b90p = data.filter(r => (parseInt(r.aging_days) || 0) > 90).length;

    const fmt_num = n => parseFloat(n.toFixed(2)).toLocaleString();
    const fmt_cur = n => "₹ " + parseFloat(n.toFixed(2)).toLocaleString("en-IN");

    const inner_html = `
<div class="gp-kpi-wrapper">
    <div class="gp-kpi-card gp-kpi-clickable" data-status="all" onclick="gp_quick_filter('all')">
        <div class="gp-kpi-label">Total Sent</div>
        <div class="gp-kpi-value" style="color:#5e64ff;">${fmt_num(totalSent)}</div>
        <div class="gp-kpi-sub">units dispatched</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="all" onclick="gp_quick_filter('all')">
        <div class="gp-kpi-label">Total Received</div>
        <div class="gp-kpi-value" style="color:#2ecc71;">${fmt_num(totalReceived)}</div>
        <div class="gp-kpi-sub">units returned</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="pending" onclick="gp_quick_filter('pending')">
        <div class="gp-kpi-label">Pending</div>
        <div class="gp-kpi-value" style="color:${totalPending > 0 ? "#e74c3c" : "#2ecc71"};">${fmt_num(totalPending)}</div>
        <div class="gp-kpi-sub">units still out</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="all" onclick="gp_quick_filter('all')">
        <div class="gp-kpi-label">Total Value</div>
        <div class="gp-kpi-value" style="color:#f39c12;font-size:17px;">${fmt_cur(totalAmount)}</div>
        <div class="gp-kpi-sub">sent amount</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="Open" onclick="gp_quick_filter('Open')">
        <div class="gp-kpi-label">Open GPs</div>
        <div class="gp-kpi-value" style="color:#f39c12;">${openCount}</div>
        <div class="gp-kpi-sub">awaiting return</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="Partial" onclick="gp_quick_filter('Partial')">
        <div class="gp-kpi-label">Partial</div>
        <div class="gp-kpi-value" style="color:#3498db;">${partialCount}</div>
        <div class="gp-kpi-sub">partially returned</div>
    </div>
    <div class="gp-kpi-card gp-kpi-clickable" data-status="Closed" onclick="gp_quick_filter('Closed')">
        <div class="gp-kpi-label">Closed</div>
        <div class="gp-kpi-value" style="color:#27ae60;">${closedCount}</div>
        <div class="gp-kpi-sub">fully returned</div>
    </div>
    ${criticalCount > 0 ? `
    <div class="gp-kpi-card gp-kpi-clickable" style="border-color:#e74c3c;background:#fff5f5;" data-status="critical" onclick="gp_quick_filter('critical')">
        <div class="gp-kpi-label" style="color:#e74c3c;">&#9888; Critical &gt;60d</div>
        <div class="gp-kpi-value" style="color:#e74c3c;">${criticalCount}</div>
        <div class="gp-kpi-sub">overdue gate passes</div>
    </div>` : ""}
</div>

<div class="gp-toolbar-row">
    <div class="gp-status-toolbar">
        <label>STATUS:</label>
        <button class="gp-filter-btn" data-status="all" onclick="gp_quick_filter('all')">All (${data.length})</button>
        <button class="gp-filter-btn" data-status="Open" onclick="gp_quick_filter('Open')">Open (${openCount})</button>
        <button class="gp-filter-btn" data-status="Partial" onclick="gp_quick_filter('Partial')">Partial (${partialCount})</button>
        <button class="gp-filter-btn" data-status="Closed" onclick="gp_quick_filter('Closed')">Closed (${closedCount})</button>
        <button class="gp-filter-btn" data-status="Non-Returnable" onclick="gp_quick_filter('Non-Returnable')">Non-Returnable (${nrCount})</button>
    </div>
    <div class="gp-view-toggle">
        <label>VIEW:</label>
        <button class="gp-view-btn" data-view="detail" onclick="gp_set_view_mode('detail')">📋 Detail</button>
        <button class="gp-view-btn" data-view="party" onclick="gp_set_view_mode('party')">👥 Party-wise Summary</button>
    </div>
</div>

<div class="gp-toolbar-row">
    <div class="gp-aging-toolbar">
        <label>AGING:</label>
        <button class="gp-aging-btn" data-bucket="all" onclick="gp_set_aging_bucket('all')">All</button>
        <button class="gp-aging-btn" data-bucket="0-30" onclick="gp_set_aging_bucket('0-30')">0–30d (${b0_30})</button>
        <button class="gp-aging-btn" data-bucket="30-60" onclick="gp_set_aging_bucket('30-60')">30–60d (${b30_60})</button>
        <button class="gp-aging-btn" data-bucket="60-90" onclick="gp_set_aging_bucket('60-90')">60–90d (${b60_90})</button>
        <button class="gp-aging-btn" data-bucket="90+" onclick="gp_set_aging_bucket('90+')">90d+ (${b90p})</button>
    </div>
    <div class="gp-search-box">
        <span class="gp-search-icon">🔍</span>
        <input id="gp-search-input" type="text" placeholder="Search party, outward #, description, vehicle..." oninput="gp_set_search(this.value)" />
    </div>
</div>

<div id="gp-party-summary-root"></div>
`;

    if (!document.getElementById("gp-kpi-style")) {
        const style = document.createElement("style");
        style.id = "gp-kpi-style";
        style.textContent = `
.gp-kpi-wrapper {
    display:flex;flex-wrap:wrap;gap:10px;padding:14px 0 6px 0;margin-bottom:6px;
}
.gp-kpi-card {
    flex:1 1 130px;min-width:120px;max-width:175px;
    border-radius:10px;padding:12px 16px;
    border:1px solid rgba(0,0,0,.08);
    background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.07);
    transition:box-shadow .2s, transform .15s;
}
.gp-kpi-clickable { cursor:pointer; user-select:none; }
.gp-kpi-card:hover { box-shadow:0 4px 14px rgba(0,0,0,.13); }
.gp-kpi-clickable:hover { transform:translateY(-2px); }
.gp-kpi-clickable:active { transform:translateY(0); }
.gp-kpi-label { font-size:11px;font-weight:600;color:#888;letter-spacing:.5px;text-transform:uppercase; }
.gp-kpi-value { font-size:22px;font-weight:700;margin-top:4px; }
.gp-kpi-sub { font-size:11px;color:#aaa;margin-top:2px; }

.gp-toolbar-row {
    display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;
    gap:10px;padding:6px 0;
}
.gp-status-toolbar, .gp-view-toggle, .gp-aging-toolbar {
    display:flex;flex-wrap:wrap;gap:6px;align-items:center;
}
.gp-status-toolbar label, .gp-view-toggle label, .gp-aging-toolbar label {
    font-size:12px;color:#888;font-weight:600;margin-right:4px;
}
.gp-filter-btn, .gp-view-btn, .gp-aging-btn {
    padding:4px 14px;border-radius:20px;font-size:12px;font-weight:600;
    cursor:pointer;border:2px solid transparent;
    transition:all .15s;background:#f1f1f1;color:#555;
}
.gp-filter-btn:hover, .gp-view-btn:hover, .gp-aging-btn:hover {
    transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,0,0,.15);
}
.gp-filter-btn[data-status="all"].active { background:#5e64ff;color:#fff; }
.gp-filter-btn[data-status="Open"].active { background:#fff3cd;color:#856404;border-color:#ffc107; }
.gp-filter-btn[data-status="Partial"].active { background:#cce5ff;color:#004085;border-color:#b8daff; }
.gp-filter-btn[data-status="Closed"].active { background:#d4edda;color:#155724;border-color:#c3e6cb; }
.gp-filter-btn[data-status="Non-Returnable"].active { background:#f8d7da;color:#721c24;border-color:#f5c6cb; }
.gp-view-btn.active { background:#2c3e50;color:#fff; }
.gp-aging-btn.active { background:#34495e;color:#fff; }
.aging-critical { background:#fff5f5 !important; }

.gp-search-box {
    display:flex;align-items:center;gap:6px;
    background:#fff;border:1px solid #ddd;border-radius:20px;
    padding:4px 12px;min-width:280px;
}
.gp-search-icon { font-size:12px;opacity:.6; }
.gp-search-box input {
    border:none;outline:none;font-size:13px;flex:1;background:transparent;
}

/* Party-wise summary table */
.gp-party-summary {
    margin:10px 0 18px 0;border:1px solid #e8e8e8;border-radius:10px;overflow:hidden;
    box-shadow:0 1px 4px rgba(0,0,0,.06);
}
.gp-party-summary table { width:100%;border-collapse:collapse;font-size:13px; }
.gp-party-summary thead th {
    background:#f8f9fb;color:#555;font-weight:700;text-align:left;
    padding:10px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.4px;
    border-bottom:2px solid #eee;cursor:pointer;white-space:nowrap;
}
.gp-party-summary thead th:hover { background:#f0f1f5; }
.gp-party-summary thead th .sort-arrow { font-size:9px;color:#aaa;margin-left:3px; }
.gp-party-summary tbody td {
    padding:9px 14px;border-bottom:1px solid #f2f2f2;
}
.gp-party-summary tbody tr:hover { background:#fafbfd; }
.gp-party-summary tbody tr:last-child td { border-bottom:none; }
.gp-party-summary .num-cell { text-align:right;font-variant-numeric:tabular-nums; }
.gp-party-summary .party-link { color:#5e64ff;font-weight:600;cursor:pointer;text-decoration:none; }
.gp-party-summary .party-link:hover { text-decoration:underline; }
.gp-party-summary .pending-badge {
    display:inline-block;padding:1px 9px;border-radius:10px;font-size:11px;font-weight:700;
}
.gp-party-summary .pending-high { background:#f8d7da;color:#721c24; }
.gp-party-summary .pending-zero { background:#d4edda;color:#155724; }
.gp-summary-footer-row td {
    background:#f8f9fb;font-weight:700;border-top:2px solid #eee;
}
.gp-empty-state {
    padding:36px 20px;text-align:center;color:#999;
    background:#fff;border:1px dashed #ddd;border-radius:10px;margin:10px 0;
}
.gp-empty-state .gp-empty-icon { font-size:28px;margin-bottom:8px; }

@media print {
    .gp-status-toolbar, .gp-view-toggle, .gp-aging-toolbar, .gp-search-box,
    .page-head, .page-actions, .standard-filter-section, .report-summary {
        display:none !important;
    }
    .gp-kpi-card:hover, .gp-kpi-clickable:hover { transform:none;box-shadow:none; }
}
        `;
        document.head.appendChild(style);
    }

    const dtWrapper = $(datatable.wrapper);
    const parentEl = dtWrapper.parent();
    let root = document.getElementById("gp-kpi-root");

    if (!root) {
        root = document.createElement("div");
        root.id = "gp-kpi-root";
        parentEl[0].insertBefore(root, dtWrapper[0]);
    }

    root.innerHTML = inner_html;

    // After (re)building the toolbar DOM, reconcile visibility + control state.
    // We do NOT call report.datatable.refresh() here (would cause infinite
    // recursion via after_datatable_render) — only show/hide + repaint summary.
    const summaryRoot = document.getElementById("gp-party-summary-root");
    if (state.view_mode === "party") {
        dtWrapper.css("display", "none");
        if (summaryRoot) {
            summaryRoot.style.display = "block";
            render_party_summary(gp_filtered_data());
        }
    } else {
        dtWrapper.css("display", "");
        if (summaryRoot) summaryRoot.style.display = "none";
    }
    sync_toolbar_controls();
}

/* ─────────────────────────────────────────────────────────────────────────
   USER ACTIONS — all funnel into gp_render()
───────────────────────────────────────────────────────────────────────── */
window.gp_quick_filter = function (status) {
    gp_state().status_filter = status;
    gp_render();
};

window.gp_set_view_mode = function (mode) {
    gp_state().view_mode = mode;
    gp_render();
};

window.gp_set_aging_bucket = function (bucket) {
    gp_state().aging_bucket = bucket;
    gp_render();
};

window.gp_set_search = function (value) {
    gp_state().search_text = value;
    clearTimeout(window._gp_search_timer);
    window._gp_search_timer = setTimeout(() => {
        gp_render();
        // Restore focus + cursor position to the search box after re-render,
        // since gp_render() rebuilds the toolbar's innerHTML.
        const input = document.getElementById("gp-search-input");
        if (input) {
            input.focus();
            const v = input.value;
            input.value = "";
            input.value = v;
        }
    }, 250);
};

window.gp_drill_party = function (party_name) {
    gp_state().view_mode = "detail";
    gp_state().status_filter = "all";
    gp_state().aging_bucket = "all";
    gp_state().search_text = party_name;
    gp_render();
};

window.gp_sort_summary = function (field) {
    const s = gp_state().sort;
    if (s.field === field) {
        s.dir = s.dir === "asc" ? "desc" : "asc";
    } else {
        s.field = field;
        s.dir = "desc";
    }
    render_party_summary(gp_filtered_data());
};

/* ─────────────────────────────────────────────────────────────────────────
   PARTY-WISE SUMMARY — aggregate filtered rows by party_name
───────────────────────────────────────────────────────────────────────── */
function build_party_summary_rows(data) {
    const map = {};

    data.forEach(r => {
        const key = `${r.party_type || "—"}::${r.party_name || "Unknown"}`;
        if (!map[key]) {
            map[key] = {
                party_type: r.party_type || "—",
                party_name: r.party_name || "Unknown",
                gp_count: new Set(),
                sent_qty: 0,
                received_qty: 0,
                pending_qty: 0,
                total_amount: 0,
                open_count: 0,
                partial_count: 0,
                closed_count: 0,
                max_aging: 0,
            };
        }
        const m = map[key];
        m.gp_count.add(r.outward_no);
        m.sent_qty += flt(r.sent_qty);
        m.received_qty += flt(r.total_received);
        m.pending_qty += flt(r.pending_qty);
        m.total_amount += flt(r.total_amount);
        if (r.gp_status === "Open") m.open_count++;
        if (r.gp_status === "Partial") m.partial_count++;
        if (r.gp_status === "Closed") m.closed_count++;
        if (r.gp_status !== "Non-Returnable") {
            m.max_aging = Math.max(m.max_aging, parseInt(r.aging_days) || 0);
        }
    });

    return Object.values(map).map(m => ({
        party_type: m.party_type,
        party_name: m.party_name,
        gp_count: m.gp_count.size,
        sent_qty: m.sent_qty,
        received_qty: m.received_qty,
        pending_qty: m.pending_qty,
        total_amount: m.total_amount,
        open_count: m.open_count,
        partial_count: m.partial_count,
        closed_count: m.closed_count,
        max_aging: m.max_aging,
    }));
}

function render_party_summary(filteredData) {
    const root = document.getElementById("gp-party-summary-root");
    if (!root) return;

    let rows = build_party_summary_rows(filteredData || []);

    const { field, dir } = gp_state().sort;
    rows.sort((a, b) => {
        let av = a[field], bv = b[field];
        if (typeof av === "string") {
            return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
        }
        return dir === "asc" ? av - bv : bv - av;
    });

    if (!rows.length) {
        root.innerHTML = `<div class="gp-empty-state">
            <div class="gp-empty-icon">📭</div>
            <div>No gate passes match the current filters.</div>
        </div>`;
        return;
    }

    const fmt_num = n => parseFloat(n.toFixed(2)).toLocaleString();
    const fmt_cur = n => "₹ " + parseFloat(n.toFixed(2)).toLocaleString("en-IN");

    const col_def = [
        { field: "party_type", label: "Type", align: "left" },
        { field: "party_name", label: "Party Name", align: "left" },
        { field: "gp_count", label: "GP Count", align: "right" },
        { field: "sent_qty", label: "Sent Qty", align: "right" },
        { field: "received_qty", label: "Received Qty", align: "right" },
        { field: "pending_qty", label: "Pending Qty", align: "right" },
        { field: "total_amount", label: "Sent Value", align: "right" },
        { field: "open_count", label: "Open", align: "right" },
        { field: "partial_count", label: "Partial", align: "right" },
        { field: "max_aging", label: "Max Aging", align: "right" },
    ];

    const totals = rows.reduce((acc, r) => {
        acc.gp_count += r.gp_count;
        acc.sent_qty += r.sent_qty;
        acc.received_qty += r.received_qty;
        acc.pending_qty += r.pending_qty;
        acc.total_amount += r.total_amount;
        acc.open_count += r.open_count;
        acc.partial_count += r.partial_count;
        return acc;
    }, { gp_count: 0, sent_qty: 0, received_qty: 0, pending_qty: 0, total_amount: 0, open_count: 0, partial_count: 0 });

    const thead = col_def.map(c => {
        const arrow = gp_state().sort.field === c.field
            ? (gp_state().sort.dir === "asc" ? "▲" : "▼")
            : "";
        return `<th style="text-align:${c.align};" onclick="gp_sort_summary('${c.field}')">
            ${c.label} <span class="sort-arrow">${arrow}</span>
        </th>`;
    }).join("");

    const tbody = rows.map(r => {
        const pendingClass = r.pending_qty > 0 ? "pending-high" : "pending-zero";
        return `<tr>
            <td>${r.party_type}</td>
            <td><a class="party-link" onclick="gp_drill_party('${r.party_name.replace(/'/g, "\\'")}')">${r.party_name}</a></td>
            <td class="num-cell">${r.gp_count}</td>
            <td class="num-cell">${fmt_num(r.sent_qty)}</td>
            <td class="num-cell">${fmt_num(r.received_qty)}</td>
            <td class="num-cell"><span class="pending-badge ${pendingClass}">${fmt_num(r.pending_qty)}</span></td>
            <td class="num-cell">${fmt_cur(r.total_amount)}</td>
            <td class="num-cell">${r.open_count}</td>
            <td class="num-cell">${r.partial_count}</td>
            <td class="num-cell">${r.max_aging}d</td>
        </tr>`;
    }).join("");

    root.innerHTML = `
        <div class="gp-party-summary">
            <table>
                <thead><tr>${thead}</tr></thead>
                <tbody>${tbody}</tbody>
                <tfoot>
                    <tr class="gp-summary-footer-row">
                        <td colspan="2">TOTAL (${rows.length} parties)</td>
                        <td class="num-cell">${totals.gp_count}</td>
                        <td class="num-cell">${fmt_num(totals.sent_qty)}</td>
                        <td class="num-cell">${fmt_num(totals.received_qty)}</td>
                        <td class="num-cell">${fmt_num(totals.pending_qty)}</td>
                        <td class="num-cell">${fmt_cur(totals.total_amount)}</td>
                        <td class="num-cell">${totals.open_count}</td>
                        <td class="num-cell">${totals.partial_count}</td>
                        <td class="num-cell">—</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    `;
}

/* ─────────────────────────────────────────────────────────────────────────
   EXPORT — Party Summary to CSV
───────────────────────────────────────────────────────────────────────── */
function gp_export_party_csv() {
    const rows = build_party_summary_rows(gp_filtered_data());
    if (!rows.length) {
        frappe.msgprint(__("No data to export for the current filters."));
        return;
    }

    const headers = [
        "Party Type", "Party Name", "GP Count", "Sent Qty", "Received Qty",
        "Pending Qty", "Sent Value", "Open", "Partial", "Closed", "Max Aging (Days)"
    ];

    const escape_csv = (val) => {
        const s = String(val ?? "");
        if (s.includes(",") || s.includes('"') || s.includes("\n")) {
            return `"${s.replace(/"/g, '""')}"`;
        }
        return s;
    };

    const lines = [headers.join(",")];
    rows.forEach(r => {
        lines.push([
            r.party_type, r.party_name, r.gp_count, r.sent_qty, r.received_qty,
            r.pending_qty, r.total_amount, r.open_count, r.partial_count,
            r.closed_count, r.max_aging
        ].map(escape_csv).join(","));
    });

    const csv_content = lines.join("\n");
    const blob = new Blob([csv_content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Gate_Pass_Party_Summary_${frappe.datetime.get_today()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}


/* ─────────────────────────────────────────────────────────────────────────
   UTILITY
───────────────────────────────────────────────────────────────────────── */
function flt(val) {
    return parseFloat(val) || 0;
}