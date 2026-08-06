(() => {
    "use strict";

    if (window.__custom_report_export_loaded) {
        return;
    }
    window.__custom_report_export_loaded = true;

    // Distinct label + class so this never collides with Frappe's own
    // "Export Excel" / "Export" button - that one is left completely
    // alone and keeps its standard dialog behavior.
    const BUTTON_LABEL = __("Download Excel");
    const BUTTON_CLASS = "custom-download-excel-btn";

    function download_custom_excel(report) {

        if (!report || !report.report_name) {
            frappe.show_alert({
                message: __("Could not detect the current report."),
                indicator: "red",
            });
            return;
        }

        const filters = report.get_filter_values ? report.get_filter_values(true) : {};

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
        } else if (frappe && frappe.utils && typeof frappe.utils.open_url_post === "function") {
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
            document.body.appendChild(form);
            form.submit();
            form.remove();
        }
    }

    function add_export_button(report) {
        if (!report || !report.page) {
            return;
        }

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {

                // Remove any previous copy of OUR button only - never
                // touches Frappe's native Export Excel / Export button.
                report.page.wrapper.find("." + BUTTON_CLASS).remove();

                report.page.add_inner_button(BUTTON_LABEL, () => {
                    download_custom_excel(report);
                });

                report.page.wrapper
                    .find(".inner-group-button, .btn")
                    .filter(function () {
                        return $(this).text().trim() === BUTTON_LABEL;
                    })
                    .first()
                    .addClass(BUTTON_CLASS);
            });
        });
    }

    const QueryReport = frappe.views.QueryReport;

    // No override of export_report anymore - the standard "Export
    // Excel"/"Export" button and its dialog run exactly as Frappe
    // ships them, untouched.

    const original_refresh_report = QueryReport.prototype.refresh_report;
    QueryReport.prototype.refresh_report = async function (...args) {
        const result = await original_refresh_report.apply(this, args);
        add_export_button(this);
        return result;
    };

    const original_show = QueryReport.prototype.show;
    QueryReport.prototype.show = async function (...args) {
        const result = await original_show.apply(this, args);
        add_export_button(this);
        return result;
    };
})();