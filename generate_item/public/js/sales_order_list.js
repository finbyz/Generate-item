// frappe.listview_settings["Sales Order"] = {

//     onload: function (listview) {

//         function get_saved_palette() {
//             let saved = localStorage.getItem("sales_order_palette");
//             if (saved) return JSON.parse(saved);
//             return [
//                 { status: "Overdue",             bg_color: "#fff1f0", border_color: "#ff4d4f" },
//                 { status: "To Deliver and Bill", bg_color: "#fff7e6", border_color: "#fa8c16" },
//                 { status: "Completed",           bg_color: "#f6ffed", border_color: "#52c41a" },
//                 { status: "Draft",               bg_color: "#e6f4ff", border_color: "#1677ff" },
//                 { status: "Submitted",           bg_color: "#f0f4ff", border_color: "#5b7fff" },
//             ];
//         }

//         function apply_row_colors() {
//             let palette = get_saved_palette();

//             $(".list-row-container").each(function () {
//                 let row = $(this);

//                 // Reset previous styles first
//                 row.css({
//                     "background":    "",
//                     "border-left":   "",
//                     "border-radius": "",
//                     "margin-bottom": "",
//                     "padding-left":  "",
//                 });
//                 row.find(".list-row").css("background", "");

//                 // Get status text from indicator pill
//                 let status = row.find(".indicator-pill").first().text().trim();
//                 if (!status) return;

//                 let match = palette.find(x => x.status === status);
//                 if (!match) return;

//                 // ── Apply to outer container ──
//                 row.css({
//                     "background":    match.bg_color,
//                     "border-left":   `5px solid ${match.border_color}`,
//                     "border-radius": "8px",
//                     "margin-bottom": "5px",
//                     "padding-left":  "4px",
//                     "transition":    "all 0.2s ease",
//                 });

//                 // ── Also apply to inner .list-row (Frappe v14/v15 uses this) ──
//                 row.find(".list-row").css({
//                     "background":    match.bg_color,
//                     "border-radius": "8px",
//                 });

//                 // ── Force all child divs to inherit background ──
//                 row.find(".list-row-col, .level, .level-left, .level-right").css({
//                     "background": "transparent",
//                 });
//             });
//         }

//         function inject_custom_css() {
//             if (document.getElementById("sales-order-custom-row-css")) return;
//             let style = document.createElement("style");
//             style.id  = "sales-order-custom-row-css";
//             style.innerHTML = `
//                 /* Full row background coverage */
//                 .list-row-container {
//                     overflow: hidden;
//                     border-radius: 8px;
//                     margin-bottom: 5px !important;
//                 }
//                 .list-row-container .list-row {
//                     border-radius: 8px !important;
//                 }
//                 /* Remove default white/grey bg that overrides our color */
//                 .list-row-container .list-row,
//                 .list-row-container .list-row-col {
//                     background: transparent !important;
//                 }
//                 /* Hover lift effect */
//                 .list-row-container:hover {
//                     transform: translateY(-1px);
//                     box-shadow: 0 4px 14px rgba(0,0,0,0.10);
//                     filter: brightness(0.97);
//                 }
//             `;
//             document.head.appendChild(style);
//         }

//         // ── Toolbar Button ──────────────────────────────────────────
//         listview.page.add_inner_button(
//             __("Row Color Palette"),
//             function () {
//                 let d = new frappe.ui.Dialog({
//                     title: __("Manage Status Colors"),
//                     size:  "large",
//                     fields: [
//                         {
//                             fieldtype: "HTML",
//                             fieldname: "info_section",
//                             options: `
//                                 <div style="background:#f8f9fa;border:1px solid #dfe3e6;
//                                     border-radius:10px;padding:18px;margin-bottom:15px;">
//                                     <div style="font-size:15px;font-weight:600;
//                                         margin-bottom:8px;color:#2c3e50;">
//                                         List Row Color Configuration
//                                     </div>
//                                     <div style="font-size:13px;line-height:1.7;color:#555;">
//                                         Configure full row background and border colors
//                                         according to Sales Order Status.
//                                     </div>
//                                 </div>
//                             `,
//                         },
//                         {
//                             fieldname:       "palette",
//                             fieldtype:       "Table",
//                             label:           __("Status Palette"),
//                             cannot_add_rows: false,
//                             in_place_edit:   true,
//                             data:            get_saved_palette(),
//                             fields: [
//                                 { fieldtype: "Data",  fieldname: "status",       label: __("Status"),     in_list_view: 1, reqd: 1 },
//                                 { fieldtype: "Color", fieldname: "bg_color",     label: __("Background"), in_list_view: 1 },
//                                 { fieldtype: "Color", fieldname: "border_color", label: __("Border"),     in_list_view: 1 },
//                             ],
//                         },
//                     ],
//                     primary_action_label: __("Save"),
//                     primary_action(values) {
//                         localStorage.setItem(
//                             "sales_order_palette",
//                             JSON.stringify(values.palette || [])
//                         );
//                         frappe.show_alert({ message: __("Palette Updated"), indicator: "green" });
//                         d.hide();
//                         apply_row_colors();
//                     },
//                 });
//                 d.show();
//             },
//             __("Colour Pallette")
//         );

//         inject_custom_css();
//         setTimeout(() => apply_row_colors(), 600);
//     },

//     refresh: function (listview) {
//         setTimeout(() => {
//             let palette = JSON.parse(
//                 localStorage.getItem("sales_order_palette") || "[]"
//             );
//             if (!palette.length) return;

//             $(".list-row-container").each(function () {
//                 let row    = $(this);
//                 let status = row.find(".indicator-pill").first().text().trim();
//                 if (!status) return;
//                 let match  = palette.find(x => x.status === status);
//                 if (!match) return;

//                 row.css({
//                     "background":    match.bg_color,
//                     "border-left":   `5px solid ${match.border_color}`,
//                     "border-radius": "8px",
//                     "margin-bottom": "5px",
//                     "padding-left":  "4px",
//                     "transition":    "all 0.2s ease",
//                 });

//                 row.find(".list-row").css({
//                     "background":    match.bg_color,
//                     "border-radius": "8px",
//                 });

//                 row.find(".list-row-col, .level, .level-left, .level-right").css({
//                     "background": "transparent",
//                 });
//             });
//         }, 300);
//     },
// };

frappe.listview_settings["Sales Order"] = {

    onload: function (listview) {

        function get_saved_palette() {
            let saved = localStorage.getItem("sales_order_palette");
            if (saved) return JSON.parse(saved);
            return [
                { status: "Overdue",             bg_color: "#fff1f0", border_color: "#ff4d4f" },
                { status: "To Deliver and Bill", bg_color: "#fff7e6", border_color: "#fa8c16" },
                { status: "Completed",           bg_color: "#f6ffed", border_color: "#52c41a" },
                { status: "Draft",               bg_color: "#e6f4ff", border_color: "#1677ff" },
                { status: "Submitted",           bg_color: "#f0f4ff", border_color: "#5b7fff" },
            ];
        }

        function inject_palette_css(palette) {
            let old = document.getElementById("so-palette-dynamic-css");
            if (old) old.remove();

            let rules = palette.map(p => {
                let safe = p.status.replace(/"/g, '\\"');
                return `
                    /* Target the actual rendered row div in Frappe v16 */
                    .list-row-container[data-row-status="${safe}"] .level.list-row {
                        background-color: ${p.bg_color} !important;
                        border-radius: 8px !important;
                    }
                    .list-row-container[data-row-status="${safe}"] {
                        border-left: 5px solid ${p.border_color} !important;
                        border-radius: 8px !important;
                        margin-bottom: 5px !important;
                        padding-left: 2px !important;
                        transition: all 0.2s ease !important;
                    }
                `;
            }).join("\n");

            let style = document.createElement("style");
            style.id = "so-palette-dynamic-css";
            style.innerHTML = `
                .list-row-container {
                    overflow: hidden;
                    border-radius: 8px;
                    margin-bottom: 5px !important;
                }
                .list-row-container:hover .level.list-row {
                    filter: brightness(0.97);
                }
                .list-row-container:hover {
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 14px rgba(0,0,0,0.10) !important;
                }
                ${rules}
            `;
            document.head.appendChild(style);
        }

        function apply_row_colors() {
            let palette = get_saved_palette();

            $(".list-row-container").each(function () {
                let row    = $(this);
                let status = row.find(".indicator-pill").first().text().trim();

                row.removeAttr("data-row-status");
                if (!status) return;

                let match = palette.find(x => x.status === status);
                if (!match) return;

                row.attr("data-row-status", status);
            });
        }

        // ── Toolbar Button ──────────────────────────────────────────
        listview.page.add_inner_button(
            __("Row Color Palette"),
            function () {
                let d = new frappe.ui.Dialog({
                    title: __("Manage Status Colors"),
                    size:  "large",
                    fields: [
                        {
                            fieldtype: "HTML",
                            fieldname: "info_section",
                            options: `
                                <div style="background:#f8f9fa;border:1px solid #dfe3e6;
                                    border-radius:10px;padding:18px;margin-bottom:15px;">
                                    <div style="font-size:15px;font-weight:600;
                                        margin-bottom:8px;color:#2c3e50;">
                                        List Row Color Configuration
                                    </div>
                                    <div style="font-size:13px;line-height:1.7;color:#555;">
                                        Configure full row background and border colors
                                        according to Sales Order Status.
                                    </div>
                                </div>
                            `,
                        },
                        {
                            fieldname:       "palette",
                            fieldtype:       "Table",
                            label:           __("Status Palette"),
                            cannot_add_rows: false,
                            in_place_edit:   true,
                            data:            get_saved_palette(),
                            fields: [
                                { fieldtype: "Data",  fieldname: "status",       label: __("Status"),     in_list_view: 1, reqd: 1 },
                                { fieldtype: "Color", fieldname: "bg_color",     label: __("Background"), in_list_view: 1 },
                                { fieldtype: "Color", fieldname: "border_color", label: __("Border"),     in_list_view: 1 },
                            ],
                        },
                    ],
                    primary_action_label: __("Save"),
                    primary_action(values) {
                        localStorage.setItem(
                            "sales_order_palette",
                            JSON.stringify(values.palette || [])
                        );
                        frappe.show_alert({ message: __("Palette Updated"), indicator: "green" });
                        d.hide();
                        inject_palette_css(get_saved_palette());
                        apply_row_colors();
                    },
                });
                d.show();
            },
            __("Customize")
        );

        // ── Init ────────────────────────────────────────────────────
        inject_palette_css(get_saved_palette());
        setTimeout(() => apply_row_colors(), 600);
    },

    refresh: function (listview) {
        setTimeout(() => {
            let palette = JSON.parse(
                localStorage.getItem("sales_order_palette") || "[]"
            );
            if (!palette.length) return;

            $(".list-row-container").each(function () {
                let row    = $(this);
                let status = row.find(".indicator-pill").first().text().trim();
                row.removeAttr("data-row-status");
                if (!status) return;
                let match = palette.find(x => x.status === status);
                if (!match) return;
                row.attr("data-row-status", status);
            });
        }, 300);
    },
};