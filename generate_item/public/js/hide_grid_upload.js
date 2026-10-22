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
        "Sales Invoice",
        "Delivery Note",
        "Order Modification Request"
    ];

    // Check if current user is Administrator or System Manager
    function is_admin() {
        const user = frappe.session && frappe.session.user;

        return (
            user === "Administrator" ||
            frappe.user.has_role("Administrator") ||
            frappe.user.has_role("System Manager")
        );
    }

    // Inject global CSS for restricted users
    function inject_css_rules() {
        const style_id = "hide-grid-upload-global-css";
        if (is_admin()) {
            const existing = document.getElementById(style_id);
            if (existing) {
                existing.remove();
            }
            return;
        }

        if (document.getElementById(style_id)) return;

        const route_selectors = [];
        TARGET_DOCTYPES.forEach((dt) => {
            const slug = dt.toLowerCase().replace(/[^a-z0-9]/g, "-").replace(/-+/g, "-");
            const encoded = encodeURIComponent(dt);

            // Container and page selectors for Desk Form views
            route_selectors.push(`.page-container[data-page-route="${dt}"] .grid-upload`);
            route_selectors.push(`.page-container[data-page-route*="${dt}"] .grid-upload`);
            route_selectors.push(`.page-container[data-page-route*="${slug}"] .grid-upload`);
            route_selectors.push(`.page-container[data-page-route*="${encoded}"] .grid-upload`);
            route_selectors.push(`.page-container[id="page-${dt}"] .grid-upload`);
            route_selectors.push(`[data-doctype="${dt}"] .grid-upload`);

            route_selectors.push(`.page-container[data-page-route="${dt}"] [data-action="upload"]`);
            route_selectors.push(`.page-container[data-page-route*="${dt}"] [data-action="upload"]`);
            route_selectors.push(`.page-container[data-page-route*="${slug}"] [data-action="upload"]`);
            route_selectors.push(`.page-container[data-page-route*="${encoded}"] [data-action="upload"]`);
            route_selectors.push(`.page-container[id="page-${dt}"] [data-action="upload"]`);
            route_selectors.push(`[data-doctype="${dt}"] [data-action="upload"]`);

            // Body route selectors (e.g. data-route="Form/Delivery Note/DN-0001")
            route_selectors.push(`body[data-route^="Form/${dt}"] .grid-upload`);
            route_selectors.push(`body[data-route*="Form/${dt}"] .grid-upload`);
            route_selectors.push(`body[data-route*="${slug}"] .grid-upload`);

            route_selectors.push(`body[data-route^="Form/${dt}"] [data-action="upload"]`);
            route_selectors.push(`body[data-route*="Form/${dt}"] [data-action="upload"]`);
            route_selectors.push(`body[data-route*="${slug}"] [data-action="upload"]`);
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
                opacity: 0 !important;
                width: 0 !important;
                height: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
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

        inject_css_rules();

        // Mark form wrapper with CSS classes & attributes
        if (frm.wrapper) {
            $(frm.wrapper).addClass("no-grid-upload").attr("data-hide-grid-upload", "true");
            if (!frm.wrapper._hide_upload_click_bound) {
                frm.wrapper._hide_upload_click_bound = true;
                $(frm.wrapper).on("click", ".grid-upload, [data-action='upload']", function (e) {
                    e.stopImmediatePropagation();
                    e.preventDefault();
                    return false;
                });
            }
        }
        if (frm.page && frm.page.wrapper) {
            $(frm.page.wrapper).addClass("no-grid-upload").attr("data-hide-grid-upload", "true");
        }

        function clean_buttons() {
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
                if (grid) {
                    if (grid.wrapper) {
                        grid.wrapper.find(".grid-upload, [data-action='upload']").each(function () {
                            $(this).css({ display: "none" }).addClass("hidden d-none").hide();
                        });
                    }
                    if (!grid._hide_upload_patched) {
                        grid._hide_upload_patched = true;
                        const orig_refresh = grid.refresh;
                        if (orig_refresh) {
                            grid.refresh = function () {
                                const res = orig_refresh.apply(this, arguments);
                                if (this.wrapper) {
                                    this.wrapper.find(".grid-upload, [data-action='upload']").each(function () {
                                        $(this).css({ display: "none" }).addClass("hidden d-none").hide();
                                    });
                                }
                                return res;
                            };
                        }
                    }
                }
            });
        }

        clean_buttons();

        let attempts = 0;
        const max_attempts = 15;
        const interval_ms = 150;

        function attempt_hide() {
            clean_buttons();
            attempts++;
            if (attempts < max_attempts) {
                setTimeout(attempt_hide, interval_ms);
            }
        }

        attempt_hide();
    }

    // Run CSS injection immediately and on DOM/page events
    inject_css_rules();
    $(document).ready(function () {
        inject_css_rules();
    });
    $(document).on("page-change", function () {
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
