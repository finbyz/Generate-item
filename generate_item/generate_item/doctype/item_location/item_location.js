// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Location", {
    branch(frm) {
        const warehouse_map = {
            "Sanand": {
                warehouse_1: "Sanand Stores - SVIPL",
                warehouse_2: "Sanand Order Allocated - SVIPL"
            },
            "Rabale": {
                warehouse_1: "Rabale Stores - SVIPL",
                warehouse_2: "Rabale Order Allocated - SVIPL"
            },
            "Nandikoor": {
                warehouse_1: "Nandikoor Stores - SVIPL",
                warehouse_2: "Nandikoor Order Allocated - SVIPL"
            }
        };

        if (warehouse_map[frm.doc.branch]) {
            frm.set_value("warehouse_1", warehouse_map[frm.doc.branch].warehouse_1);
            frm.set_value("warehouse_2", warehouse_map[frm.doc.branch].warehouse_2);
        } else {
            frm.set_value("warehouse_1", "");
            frm.set_value("warehouse_2", "");
        }
    }
});

