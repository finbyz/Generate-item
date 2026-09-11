frappe.ui.form.on("Employee", {
    refresh(frm) {
        if (!frm.is_new()) {
            return;
        }

        set_employee_naming_series(frm);
    },

    branch(frm) {
        if (!frm.is_new()) {
            return;
        }

        set_employee_naming_series(frm);
    }
});

function set_employee_naming_series(frm) {
    const series_map = {
        "Sanand": "EMPS.fiscal.#####",
        "Rabale": "EMPR.fiscal.#####",
        "Nandikoor": "EMPN.fiscal.#####"
    };

    const branch = frm.doc.branch;

    if (series_map[branch]) {
        frm.set_value("naming_series", series_map[branch]);
    }
}