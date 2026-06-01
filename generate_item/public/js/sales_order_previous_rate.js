frappe.ui.form.on("Sales Order", {
    refresh(frm) {

        frm.add_custom_button(__("Previous Sales Rates"), async function () {

            if (!frm.doc.customer) {
                frappe.msgprint(__("Please select Customer first"));
                return;
            }
        
            let items = (frm.doc.items || [])
                .filter(d => d.item_code)
                .map(d => d.item_code);
        
            if (!items.length) {
                frappe.msgprint(__("Please add items first"));
                return;
            }
        
            frappe.dom.freeze(__("Loading Previous Rates..."));
        
            try {
        
                let response = await frappe.call({
                    method: "generate_item.api.sales_order.get_previous_sales_data",
                    args: {
                        customer: frm.doc.customer,
                        items: items
                    }
                });
        
                let data = response.message || {};
        
                const fmt = (val) => {
                    return format_currency(
                        flt(val || 0),
                        frappe.boot.sysdefaults.currency
                    );
                };
        
                const format_date = (date) => {
                    return frappe.datetime.str_to_user(date);
                };
        
                const make_rows = (rows, type) => {
        
                    if (!rows || !rows.length) {
        
                        let colspan = 3;
        
                        if (type === "other_customer") colspan = 4;
        
                        return `
                            <tr>
                                <td colspan="${colspan}"
                                    style="text-align:center;color:#888;">
                                    No Records Found
                                </td>
                            </tr>
                        `;
                    }
        
                    return rows.map(row => {
        
                        if (type === "same_customer") {
        
                            return `
                                <tr>
                                    <td>
                                        <a href="/app/sales-invoice/${row.parent}"
                                           target="_blank">
                                           ${row.parent}
                                        </a>
                                    </td>
                                    <td>${fmt(row.rate)}</td>
                                    <td>${format_date(row.creation)}</td>
                                </tr>
                            `;
                        }
        
                        if (type === "other_customer") {
        
                            return `
                                <tr>
                                    <td>
                                        <a href="/app/sales-invoice/${row.parent}"
                                           target="_blank">
                                           ${row.parent}
                                        </a>
                                    </td>
                                    <td>${row.customer}</td>
                                    <td>${fmt(row.rate)}</td>
                                    <td>${format_date(row.creation)}</td>
                                </tr>
                            `;
                        }
        
                        if (type === "quotation") {
        
                            return `
                                <tr>
                                    <td>
                                        <a href="/app/quotation/${row.parent}"
                                           target="_blank">
                                           ${row.parent}
                                        </a>
                                    </td>
                                    <td>${fmt(row.rate)}</td>
                                    <td>${format_date(row.creation)}</td>
                                </tr>
                            `;
                        }
        
                        if (type === "purchase") {
        
                            return `
                                <tr>
                                    <td>
                                        <a href="/app/purchase-invoice/${row.parent}"
                                           target="_blank">
                                           ${row.parent}
                                        </a>
                                    </td>
                                    <td>${fmt(row.rate)}</td>
                                    <td>${format_date(row.creation)}</td>
                                </tr>
                            `;
                        }
        
                    }).join("");
                };
        
                let html = `<div class="psr-container">
        
               <style>

                .psr-container{
                    padding:10px;
                    background:#f4f7fb;
                }

                .psr-card{
                    background:#fff;
                    border-radius:14px;
                    margin-bottom:30px;
                    overflow:hidden;
                    box-shadow:
                        0 2px 6px rgba(0,0,0,0.05),
                        0 8px 24px rgba(0,0,0,0.04);
                    border:1px solid #e5e9f2;
                }

                .psr-header{
                    background:linear-gradient(135deg,#1e3a5f,#294b78);
                    color:white;
                    padding:18px 22px;
                    font-size:18px;
                    font-weight:700;
                    letter-spacing:.3px;
                    position:sticky;
                    top:0;
                    z-index:1;
                }

                .psr-item-subtitle{
                    margin-top:4px;
                    font-size:12px;
                    opacity:.85;
                    font-weight:400;
                }

                .psr-section{
                    padding:18px 22px;
                    border-bottom:1px solid #edf2f7;
                }

                .psr-section:last-child{
                    border-bottom:none;
                }

                .psr-title{
                    display:flex;
                    align-items:center;
                    gap:10px;
                    font-size:14px;
                    font-weight:700;
                    margin-bottom:14px;
                    color:#243447;
                    letter-spacing:.2px;
                }

                .psr-badge{
                    display:inline-flex;
                    align-items:center;
                    padding:3px 10px;
                    border-radius:30px;
                    font-size:11px;
                    font-weight:600;
                    background:#e8f1ff;
                    color:#205ecf;
                }

                .psr-table{
                    width:100%;
                    border-collapse:separate;
                    border-spacing:0;
                    overflow:hidden;
                    border-radius:10px;
                    border:1px solid #e8edf5;
                }

                .psr-table th{
                    background:#f8fafc;
                    color:#5c6b7a;
                    font-size:12px;
                    font-weight:700;
                    padding:11px 12px;
                    border-bottom:1px solid #e5e9f2;
                    text-transform:uppercase;
                    letter-spacing:.4px;
                }

                .psr-table td{
                    padding:11px 12px;
                    font-size:13px;
                    color:#2d3748;
                    border-bottom:1px solid #edf2f7;
                }

                .psr-table tr:last-child td{
                    border-bottom:none;
                }

                .psr-table tbody tr:nth-child(even){
                    background:#fbfcfe;
                }

                .psr-table tbody tr:hover{
                    background:#f1f6ff;
                    transition:.2s ease;
                }

                .psr-table a{
                    color:#205ecf;
                    font-weight:600;
                    text-decoration:none;
                }

                .psr-table a:hover{
                    text-decoration:underline;
                }

                .psr-rate{
                    color:#15803d;
                    font-weight:700;
                    font-size:13px;
                }

                .psr-empty{
                    text-align:center;
                    color:#94a3b8;
                    font-style:italic;
                    padding:16px !important;
                }

                .psr-valuation-box{
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    background:linear-gradient(135deg,#f0fff4,#ecfdf3);
                    border:1px solid #bbf7d0;
                    border-radius:12px;
                    padding:18px 20px;
                }

                .psr-valuation-label{
                    font-size:14px;
                    font-weight:600;
                    color:#166534;
                }

                .psr-valuation{
                    font-size:26px;
                    font-weight:800;
                    color:#15803d;
                    letter-spacing:.3px;
                }

                .psr-divider{
                    height:1px;
                    background:#edf2f7;
                    margin:16px 0;
                }

                @media (max-width:768px){

                    .psr-header{
                        font-size:15px;
                        padding:14px;
                    }

                    .psr-section{
                        padding:14px;
                    }

                    .psr-table th,
                    .psr-table td{
                        padding:8px;
                        font-size:11px;
                    }

                    .psr-valuation{
                        font-size:20px;
                    }
                }

                </style>
        
                `;
        
                for (let item of items) {
        
                    let row = data[item] || {};
        
                    html += `
        
                        <div class="psr-card">
        
                            <div class="psr-header">
                                ${item}
                            </div>
        
                            <div class="psr-section">
        
                                <div class="psr-title">
                                    1. Previous Sales Rate — Same Customer
                                </div>
        
                                <table class="psr-table">
        
                                    <tr>
                                        <th>Sales Invoice</th>
                                        <th>Rate</th>
                                        <th>Date</th>
                                    </tr>
        
                                    ${make_rows(
                                        row.same_customer_sales,
                                        "same_customer"
                                    )}
        
                                </table>
        
                            </div>
        
                            <div class="psr-section">
        
                                <div class="psr-title">
                                    2. Previous Sales Rate — Other Customers
                                </div>
        
                                <table class="psr-table">
        
                                    <tr>
                                        <th>Sales Invoice</th>
                                        <th>Customer</th>
                                        <th>Rate</th>
                                        <th>Date</th>
                                    </tr>
        
                                    ${make_rows(
                                        row.other_customer_sales,
                                        "other_customer"
                                    )}
        
                                </table>
        
                            </div>
        
                            <div class="psr-section">
        
                                <div class="psr-title">
                                    3. Quotation Rate
                                </div>
        
                                <table class="psr-table">
        
                                    <tr>
                                        <th>Quotation</th>
                                        <th>Rate</th>
                                        <th>Date</th>
                                    </tr>
        
                                    ${make_rows(
                                        row.quotation_rates,
                                        "quotation"
                                    )}
        
                                </table>
        
                            </div>
        
                            <div class="psr-section">
        
                                <div class="psr-title">
                                    4. Purchase Rate
                                </div>
        
                                <table class="psr-table">
        
                                    <tr>
                                        <th>Purchase Invoice</th>
                                        <th>Rate</th>
                                        <th>Date</th>
                                    </tr>
        
                                    ${make_rows(
                                        row.purchase_rates,
                                        "purchase"
                                    )}
        
                                </table>
        
                            </div>
        
                            <div class="psr-section">

                        <div class="psr-title">
                            5. Valuation Rate
                        </div>

                        <div class="psr-valuation-box">

                            <div class="psr-valuation-label">
                                Current Inventory Valuation
                            </div>

                            <div class="psr-valuation">
                                ${fmt(row.valuation_rate)}
                            </div>

                        </div>

                    </div>
        
                    `
                }
        
                let d = new frappe.ui.Dialog({
                    title: __("Previous Sales Rates"),
                    size: "extra-large",
                    fields: [
                        {
                            fieldtype: "HTML",
                            fieldname: "html"
                        }
                    ]
                });
        
                d.fields_dict.html.$wrapper.html(html);
        
                d.$wrapper.find(".modal-body").css({
                    "max-height": "75vh",
                    "overflow-y": "auto"
                });
        
                d.show();
        
            } catch (e) {
        
                console.error(e);
        
                frappe.msgprint({
                    title: __("Error"),
                    indicator: "red",
                    message: __("Failed to load previous sales rates")
                });
        
            }
        
            frappe.dom.unfreeze();
        
        });
    }
});














frappe.ui.form.on("Sales Order", {
    refresh(frm) {

        frm.add_custom_button(__("Sales Intelligence"), async function () {

            if (!frm.doc.customer) {
                frappe.msgprint(__("Please select Customer first"));
                return;
            }

            let items = (frm.doc.items || [])
                .filter(d => d.item_code)
                .map(d => d.item_code);

            if (!items.length) {
                frappe.msgprint(__("Please add items first"));
                return;
            }

            frappe.dom.freeze(__("Loading Sales Intelligence..."));

            try {

                let response = await frappe.call({
                    method: "generate_item.api.sales_order.get_previous_sales_data",
                    args: {
                        customer: frm.doc.customer,
                        items: items
                    }
                });

                let data = response.message || {};

                open_sales_intelligence_workspace(frm, data);

            } catch (e) {

                console.error(e);

                frappe.msgprint({
                    title: __("Error"),
                    indicator: "red",
                    message: __("Failed to load sales intelligence")
                });

            }

            frappe.dom.unfreeze();

        }, __("Tools"));
    }
});

function open_sales_intelligence_workspace(frm, data) {

    $(".sales-intelligence-overlay").remove();

    let items = Object.keys(data);

    let html = `
    
    <div class="sales-intelligence-overlay">

        <div class="si-backdrop"></div>

        <div class="si-workspace">

            <div class="si-header">

                <div class="si-header-left">

                    <div class="si-title">
                        Sales Intelligence
                    </div>

                    <div class="si-subtitle">
                        Customer: ${frm.doc.customer}
                    </div>

                </div>

                <div class="si-header-right">

                    <input
                        type="text"
                        class="form-control si-search"
                        placeholder="Search Item..."
                    >

                    <button class="btn btn-default si-close">
                        Close
                    </button>

                </div>

            </div>

            <div class="si-body">

                <div class="si-sidebar">

                    ${render_sidebar(items, data)}

                </div>

                <div class="si-content">

                    <div class="si-empty-state">
                        Select Item to View Intelligence
                    </div>

                </div>

            </div>

        </div>

    </div>

    ${get_sales_intelligence_styles()}
    `;

    $("body").append(html);

    bind_workspace_events(frm, data);
}

function render_sidebar(items, data) {

    return items.map((item, index) => {

        let row = data[item] || {};

        return `
            <div 
                class="si-item-card ${index === 0 ? 'active' : ''}"
                data-item="${item}"
            >

                <div class="si-item-name">
                    ${item}
                </div>

                <div class="si-item-meta">

                    <span class="indicator blue">
                        Last:
                        ${format_currency(
                            row.same_customer_sales?.[0]?.rate || 0
                        )}
                    </span>

                    <span class="indicator green">
                        Val:
                        ${format_currency(
                            row.valuation_rate || 0
                        )}
                    </span>

                </div>

            </div>
        `;

    }).join("");
}

function bind_workspace_events(frm, data) {

    let first_item = Object.keys(data)[0];

    render_item_workspace(frm, first_item, data[first_item]);

    $(".si-item-card").on("click", function () {

        $(".si-item-card").removeClass("active");

        $(this).addClass("active");

        let item = $(this).data("item");

        render_item_workspace(frm, item, data[item]);

    });

    $(".si-close, .si-backdrop").on("click", function () {
        $(".sales-intelligence-overlay").remove();
    });

    $(".si-search").on("keyup", function () {

        let val = $(this).val().toLowerCase();

        $(".si-item-card").each(function () {

            let txt = $(this).text().toLowerCase();

            $(this).toggle(txt.includes(val));

        });
    });
}

function render_item_workspace(frm, item_code, row) {

    let html = `
    
    <div class="si-main-card">

        <div class="si-top-section">

            <div>

                <div class="si-item-title">
                    ${item_code}
                </div>

                <div class="si-item-desc">
                    Pricing Intelligence & Sales Analytics
                </div>

            </div>

        </div>

        ${render_summary_cards(row)}

        ${render_section(
            "Previous Sales — Same Customer",
            row.same_customer_sales,
            "sales"
        )}

        ${render_section(
            "Previous Sales — Other Customers",
            row.other_customer_sales,
            "other"
        )}

        ${render_section(
            "Quotation History",
            row.quotation_rates,
            "quotation"
        )}

        ${render_section(
            "Purchase History",
            row.purchase_rates,
            "purchase"
        )}

    </div>
    `;

    $(".si-content").html(html);

}

function render_summary_cards(row) {

    let last_rate = row.same_customer_sales?.[0]?.rate || 0;

    let valuation = row.valuation_rate || 0;

    let suggested = get_suggested_rate(row);

    return `
    
    <div class="si-summary-grid">

        <div class="si-summary-card">

            <div class="si-summary-label">
                Last Sold
            </div>

            <div class="si-summary-value">
                ${format_currency(last_rate)}
            </div>

        </div>

        <div class="si-summary-card">

            <div class="si-summary-label">
                Valuation
            </div>

            <div class="si-summary-value green">
                ${format_currency(valuation)}
            </div>

        </div>

        <div class="si-summary-card">

            <div class="si-summary-label">
                Suggested Rate
            </div>

            <div class="si-summary-value blue">
                ${format_currency(suggested)}
            </div>

        </div>


    </div>
    `;
}

function render_section(title, rows, type) {

    return `
    
    <div class="si-section">

        <div class="si-section-title">
            ${title}
        </div>

        <div class="si-rate-grid">

            ${
                rows?.length
                    ? rows.map(r => render_rate_card(r, type)).join("")
                    : `
                        <div class="si-no-data">
                            No Records Found
                        </div>
                    `
            }

        </div>

    </div>
    `;
}

function render_rate_card(row, type) {

    let route = "";

    if (type === "sales" || type === "other") {
        route = `/app/sales-invoice/${row.parent}`;
    }

    if (type === "quotation") {
        route = `/app/quotation/${row.parent}`;
    }

    if (type === "purchase") {
        route = `/app/purchase-invoice/${row.parent}`;
    }

    return `
    
    <div class="si-rate-card">

        <div class="si-rate-top">

            <a href="${route}" target="_blank">
                ${row.parent}
            </a>

            <div class="si-rate-value">
                ${format_currency(row.rate || 0)}
            </div>

        </div>

        ${
            row.customer
                ? `
                    <div class="si-customer">
                        ${row.customer}
                    </div>
                `
                : ``
        }

        <div class="si-rate-date">
            ${frappe.datetime.str_to_user(row.creation)}
        </div>

    </div>
    `;
}
    

function get_suggested_rate(row) {

    let rates = [];

    (row.same_customer_sales || []).forEach(d => {
        if (d.rate) rates.push(flt(d.rate));
    });

    (row.other_customer_sales || []).forEach(d => {
        if (d.rate) rates.push(flt(d.rate));
    });

    if (!rates.length) {
        return flt(row.valuation_rate || 0);
    }

    let avg =
        rates.reduce((a, b) => a + b, 0) / rates.length;

    return Math.round(avg);
}

function get_sales_intelligence_styles() {

    return `
    
    <style>

    .sales-intelligence-overlay{
        position:fixed;
        inset:0;
        z-index:9999;
    }

    .si-backdrop{
        position:absolute;
        inset:0;
        background:rgba(0,0,0,.45);
        backdrop-filter:blur(3px);
    }

    .si-workspace{
        position:absolute;
        inset:20px;
        background:var(--card-bg);
        border-radius:20px;
        overflow:hidden;
        display:flex;
        flex-direction:column;
        box-shadow:0 20px 60px rgba(0,0,0,.25);
    }

    .si-header{
        height:72px;
        border-bottom:1px solid var(--border-color);
        display:flex;
        align-items:center;
        justify-content:space-between;
        padding:0 24px;
        background:var(--subtle-fg);
    }

    .si-title{
        font-size:22px;
        font-weight:700;
    }

    .si-subtitle{
        color:var(--text-muted);
        margin-top:2px;
    }

    .si-header-right{
        display:flex;
        gap:12px;
        align-items:center;
    }

    .si-search{
        width:240px;
    }

    .si-body{
        flex:1;
        display:flex;
        overflow:hidden;
    }

    .si-sidebar{
        width:300px;
        border-right:1px solid var(--border-color);
        overflow:auto;
        background:#fafbfc;
        padding:16px;
    }

    .si-content{
        flex:1;
        overflow:auto;
        padding:24px;
        background:#f7f9fb;
    }

    .si-item-card{
        background:white;
        border:1px solid var(--border-color);
        border-radius:14px;
        padding:14px;
        margin-bottom:12px;
        cursor:pointer;
        transition:.2s;
    }

    .si-item-card:hover{
        transform:translateY(-2px);
    }

    .si-item-card.active{
        border:1px solid var(--primary);
        background:#f0f4ff;
    }

    .si-item-name{
        font-weight:700;
        margin-bottom:8px;
    }

    .si-item-meta{
        display:flex;
        gap:8px;
        flex-wrap:wrap;
    }

    .si-main-card{
        background:white;
        border-radius:20px;
        padding:24px;
        border:1px solid var(--border-color);
    }

    .si-top-section{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:24px;
    }

    .si-item-title{
        font-size:28px;
        font-weight:700;
    }

    .si-item-desc{
        color:var(--text-muted);
        margin-top:4px;
    }

    .si-summary-grid{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:16px;
        margin-bottom:28px;
    }

    .si-summary-card{
        background:#f8fafc;
        border-radius:16px;
        padding:18px;
        border:1px solid var(--border-color);
    }

    .si-summary-label{
        font-size:13px;
        color:var(--text-muted);
        margin-bottom:8px;
    }

    .si-summary-value{
        font-size:26px;
        font-weight:700;
    }

    .si-summary-value.green{
        color:#15803d;
    }

    .si-summary-value.blue{
        color:#2563eb;
    }

    .si-summary-value.orange{
        color:#ea580c;
    }

    .si-section{
        margin-bottom:32px;
    }

    .si-section-title{
        font-size:18px;
        font-weight:700;
        margin-bottom:16px;
    }

    .si-rate-grid{
        display:grid;
        grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
        gap:16px;
    }

    .si-rate-card{
        background:#fff;
        border:1px solid var(--border-color);
        border-radius:16px;
        padding:18px;
    }

    .si-rate-top{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:10px;
    }

    .si-rate-top a{
        font-weight:700;
        color:var(--primary);
    }

    .si-rate-value{
        font-size:20px;
        font-weight:700;
        color:#15803d;
    }

    .si-customer{
        margin-bottom:8px;
        color:var(--text-muted);
    }

    .si-rate-date{
        font-size:12px;
        color:var(--text-muted);
        margin-bottom:16px;
    }

    .si-rate-actions{
        display:flex;
        gap:10px;
    }

    .si-no-data{
        background:#fff;
        border:1px dashed var(--border-color);
        border-radius:16px;
        padding:40px;
        text-align:center;
        color:var(--text-muted);
    }

    .si-empty-state{
        height:100%;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:20px;
        color:var(--text-muted);
    }

    @media(max-width:991px){

        .si-sidebar{
            width:220px;
        }

        .si-summary-grid{
            grid-template-columns:repeat(2,1fr);
        }
    }

    @media(max-width:768px){

        .si-workspace{
            inset:0;
            border-radius:0;
        }

        .si-header{
            flex-direction:column;
            height:auto;
            gap:12px;
            padding:16px;
        }

        .si-body{
            flex-direction:column;
        }

        .si-sidebar{
            width:100%;
            border-right:none;
            border-bottom:1px solid var(--border-color);
            display:flex;
            overflow:auto;
            gap:12px;
        }

        .si-item-card{
            min-width:240px;
            margin-bottom:0;
        }

        .si-summary-grid{
            grid-template-columns:1fr;
        }

        .si-top-section{
            flex-direction:column;
            align-items:flex-start;
            gap:14px;
        }
    }

    </style>
    `;
}