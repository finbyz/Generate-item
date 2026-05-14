// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Item Shortage Report Sukha"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			width: "80",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("company"),
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "MultiSelectList",
			options: "Warehouse",
			width: "100",
			get_data: function (txt) {
				return frappe.db.get_link_options("Warehouse", txt);
			},
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
		if (column.fieldname === "view" && data) {
            return `
                <button class="btn btn-xs btn-default"
                    onclick="show_view_menu(event, '${data.item_code || ""}')">
                    View ▼
                </button>
            `;
        }
		return value;
	}
};
window.show_view_menu = function(e, item_code) {
    e.stopPropagation();

    // Remove any existing dropdown
    $('.custom-view-dropdown').remove();

    const menu_items = [
        {
            label: "Stock Balance",
            action: () => {
                frappe.set_route("query-report", "Stock Balance", {
                    item_code: item_code
                });
            }
        },
        {
            label: "Stock Ledger",
            action: () => {
                frappe.set_route("query-report", "Stock Ledger", {
                    item_code: item_code
                });
            }
        },
        {
            label: "Stock Projected Qty",
            action: () => {
                frappe.set_route("query-report", "Stock Projected Qty", {
                    item_code: item_code
                });
            }
        }
    ];

    // Build dropdown HTML
    const dropdown = $(`
        <div class="custom-view-dropdown dropdown-menu show" 
             style="position:fixed; z-index:9999; background:white; 
                    border:1px solid #ccc; border-radius:4px; 
                    box-shadow:0 4px 8px rgba(0,0,0,0.15); min-width:180px;">
        </div>
    `);

    menu_items.forEach(item => {
        const el = $(`<a class="dropdown-item" style="padding:8px 16px; cursor:pointer; display:block;">${item.label}</a>`);
        el.on('click', () => {
            dropdown.remove();
            item.action();
        });
        el.hover(
            function() { $(this).css('background', '#f0f0f0'); },
            function() { $(this).css('background', ''); }
        );
        dropdown.append(el);
    });

    // Position near the button
    const btn = $(e.target);
    const offset = btn.offset();
    dropdown.css({
        top: offset.top + btn.outerHeight() + 2,
        left: offset.left
    });

    $('body').append(dropdown);

    // Close on outside click
    setTimeout(() => {
        $(document).one('click', () => dropdown.remove());
    }, 0);
};