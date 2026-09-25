frappe.provide("generate_item");

(function () {
    // List of doctypes where upload button should be hidden
    const TARGET_DOCTYPES = [
        "Sales Order",
        "BOM",
        "Bom Modification Request",
        "Material Request",
        "Purchase Order",
        "Purchase Receipt",
        "Work Order",
        "Stock Entry",
        "Order Modification Request"
    ];

    // Check if current user is Administrator or System Manager
    function is_admin() {
        return (
            frappe.session.user === "Administrator" ||
            frappe.user.has_role("Administrator") ||
            frappe.user.has_role("System Manager")
        );
    }

    // Inject global CSS for non-admin users
    function inject_css_rules() {
        if (is_admin()) return;

        const style_id = "hide-grid-upload-global-css";
        if (document.getElementById(style_id)) return;

        // Build selectors for both slugified routes (e.g. purchase-order) and standard doctype names
        const route_selectors = [];
        TARGET_DOCTYPES.forEach((dt) => {
            const slug = dt.toLowerCase().replace(/[^a-z0-9]/g, "-").replace(/-+/g, "-");
            route_selectors.push(`.page-container[data-page-route*="${slug}"] .grid-upload`);
            route_selectors.push(`.page-container[data-page-route*="${encodeURIComponent(dt)}"] .grid-upload`);
            route_selectors.push(`[data-doctype="${dt}"] .grid-upload`);
        });

        route_selectors.push(".no-grid-upload .grid-upload");
        route_selectors.push("[data-hide-grid-upload='true'] .grid-upload");
        route_selectors.push(".no-grid-upload [data-action='upload']");
        route_selectors.push("[data-hide-grid-upload='true'] [data-action='upload']");

        const css = `
            ${route_selectors.join(",\n")} {
                display: none !important;
                visibility: hidden !important;
                pointer-events: none !important;
            }
        `;

        const style = document.createElement("style");
        style.id = style_id;
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
    }

    // Shared function to hide the Upload button on all child tables
    function hide_grid_upload_buttons(frm) {
        if (!frm || is_admin()) return;

        // Mark form wrapper with CSS classes
        if (frm.wrapper) {
            $(frm.wrapper).addClass("no-grid-upload").attr("data-hide-grid-upload", "true");
        }
        if (frm.page && frm.page.wrapper) {
            $(frm.page.wrapper).addClass("no-grid-upload").attr("data-hide-grid-upload", "true");
        }

        let attempts = 0;
        const max_attempts = 12;
        const interval_ms = 150;

        function attempt_hide() {
            if (frm.wrapper) {
                $(frm.wrapper).find(".grid-upload, [data-action='upload']").each(function () {
                    $(this).css({ display: "none" }).addClass("hidden d-none").hide();
                });
            }

            const table_fields = (frm.meta?.fields || []).filter(
                (df) => df.fieldtype === "Table" || df.fieldtype === "Table MultiSelect"
            );

            table_fields.forEach((df) => {
                const grid = frm.fields_dict[df.fieldname]?.grid;
                if (grid && grid.wrapper) {
                    const upload_btn = grid.wrapper.find(".grid-upload, [data-action='upload']");
                    if (upload_btn.length) {
                        upload_btn.css({ display: "none" }).addClass("hidden d-none").hide();
                    }
                }
            });

            attempts++;
            if (attempts < max_attempts) {
                setTimeout(attempt_hide, interval_ms);
            }
        }

        attempt_hide();
    }

    // Run CSS injection immediately and on DOM ready
    inject_css_rules();
    $(document).ready(function () {
        inject_css_rules();
    });

    // Register all doctypes in a single loop
    TARGET_DOCTYPES.forEach((doctype) => {
        frappe.ui.form.on(doctype, {
            setup: function (frm) {
                hide_grid_upload_buttons(frm);
            },
            onload: function (frm) {
                hide_grid_upload_buttons(frm);
            },
            refresh: function (frm) {
                hide_grid_upload_buttons(frm);
            },
            onload_post_render: function (frm) {
                hide_grid_upload_buttons(frm);
            }
        });
    });
})();
