(() => {
    "use strict";

    const BUTTON_LABEL = __("Download Excel");
    const BUTTON_CLASS = "custom-download-excel-btn";

    function download_custom_excel(report) {
        report = report || frappe.query_report;

        if (!report || !report.report_name) {
            frappe.show_alert({
                message: __("Could not detect the current report."),
                indicator: "red",
            });
            return;
        }

        let filters = {};
        if (typeof report.get_filter_values === "function") {
            filters = report.get_filter_values(true) || {};
        } else if (typeof report.get_values === "function") {
            filters = report.get_values() || {};
        }

        const params = {
            report_name: report.report_name,
            filters: filters || {},
            file_format_type: "Excel",
        };

        const url = "/api/method/generate_item.generate_item.api.export_query_report";

        frappe.show_alert({
            message: __("Preparing Excel..."),
            indicator: "green",
        });

        if (typeof open_url_post === "function") {
            open_url_post(url, { form_params: JSON.stringify(params) });
        } else if (frappe?.utils?.open_url_post && typeof frappe.utils.open_url_post === "function") {
            frappe.utils.open_url_post(url, { form_params: JSON.stringify(params) });
        } else {
            const form = document.createElement("form");
            form.method = "POST";
            form.action = url;
            form.style.display = "none";

            const input = document.createElement("input");
            input.name = "form_params";
            input.value = JSON.stringify(params);
            form.appendChild(input);

            if (frappe.csrf_token && frappe.csrf_token !== "None") {
                const csrf = document.createElement("input");
                csrf.name = "csrf_token";
                csrf.value = frappe.csrf_token;
                form.appendChild(csrf);
            }

            document.body.appendChild(form);
            form.submit();
            form.remove();
        }
    }

    function add_export_button(report) {
        report = report || frappe.query_report;
        if (!report || !report.page || !report.page.wrapper) {
            return;
        }

        // Avoid duplicate buttons
        if (report.page.wrapper.find("." + BUTTON_CLASS).length > 0) {
            return;
        }

        const $btn = report.page.add_inner_button(BUTTON_LABEL, () => {
            download_custom_excel(report);
        });

        if ($btn) {
            $btn.addClass(BUTTON_CLASS);
        }
    }

    function patch_query_report() {
        if (!frappe.views || !frappe.views.QueryReport) {
            return false;
        }

        const QueryReport = frappe.views.QueryReport;
        if (QueryReport.prototype._custom_export_patched) {
            return true;
        }
        QueryReport.prototype._custom_export_patched = true;

        const original_refresh_report = QueryReport.prototype.refresh_report;
        if (original_refresh_report) {
            QueryReport.prototype.refresh_report = async function (...args) {
                const result = await original_refresh_report.apply(this, args);
                add_export_button(this);
                return result;
            };
        }

        const original_show = QueryReport.prototype.show;
        if (original_show) {
            QueryReport.prototype.show = async function (...args) {
                const result = await original_show.apply(this, args);
                add_export_button(this);
                return result;
            };
        }

        const original_render = QueryReport.prototype.render;
        if (original_render) {
            QueryReport.prototype.render = function (...args) {
                const result = original_render.apply(this, args);
                add_export_button(this);
                return result;
            };
        }

        return true;
    }

    // Expose helpers globally
    frappe.download_custom_excel = download_custom_excel;
    frappe.add_custom_report_export_button = add_export_button;

    // 1. Attempt immediate patch if QueryReport is already defined
    patch_query_report();

    // 2. Retry on page-change / route change to handle lazy loaded QueryReport
    $(document).on("page-change", () => {
        patch_query_report();
        if (frappe.query_report && frappe.get_route()?.[0] === "query-report") {
            setTimeout(() => add_export_button(frappe.query_report), 100);
        }
    });

    if (frappe.router && typeof frappe.router.on === "function") {
        frappe.router.on("change", () => {
            setTimeout(() => {
                patch_query_report();
                if (frappe.query_report && frappe.get_route()?.[0] === "query-report") {
                    add_export_button(frappe.query_report);
                }
            }, 150);
        });
    }
})();