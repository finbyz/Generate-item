import frappe


def _populate_supplied_custom_fields(doc, persist_children=False):
    if not getattr(doc, "supplied_items", None):
        return

    so_names = {
        row.subcontracting_order
        for row in doc.supplied_items
        if getattr(row, "subcontracting_order", None)
    }
    if not so_names:
        return

    so_maps = {}
    for so_name in so_names:
        try:
            so_doc = frappe.get_doc("Subcontracting Order", so_name)
        except Exception:
            continue

        by_bom_detail = {}
        by_combo = {}
        by_pair_index = {}
        for si in so_doc.supplied_items or []:
            if getattr(si, "bom_detail_no", None):
                by_bom_detail[si.bom_detail_no] = si
            # Primary triple key (handles repeated items): (rm, main, child name)
            combo_key = (
                getattr(si, "rm_item_code", None),
                getattr(si, "main_item_code", None),
                getattr(si, "name", None),
            )
            by_combo[combo_key] = si
            # Secondary index by pair for fallback disambiguation
            pair_key = (getattr(si, "rm_item_code", None), getattr(si, "main_item_code", None))
            by_pair_index.setdefault(pair_key, []).append(si)

        so_maps[so_name] = {
            "by_bom_detail": by_bom_detail,
            "by_combo": by_combo,
            "by_pair_index": by_pair_index,
        }

    custom_fields = (
        "custom_batch_no",
        "custom_drawing_no",
        "custom_drawing_rev_no",
        "custom_pattern_drawing_no",
        "custom_pattern_drawing_rev_no",
        "custom_purchase_specification_no",
        "custom_purchase_specification_rev_no",
    )

    for row in doc.supplied_items:
        so_name = getattr(row, "subcontracting_order", None)
        if not so_name or so_name not in so_maps:
            continue

        maps = so_maps[so_name]
        src = None

        bdn = getattr(row, "bom_detail_no", None)
        if bdn and bdn in maps["by_bom_detail"]:
            src = maps["by_bom_detail"][bdn]
        else:
            # Try triple with reference_name (expected to map to SO child name in many mappings)
            ref = getattr(row, "reference_name", None) or getattr(row, "name", None)
            key3 = (getattr(row, "rm_item_code", None), getattr(row, "main_item_code", None), ref)
            src = maps["by_combo"].get(key3)
            if not src:
                # Fallback to pair match; if exactly one match for the pair, use it
                pair_key = (getattr(row, "rm_item_code", None), getattr(row, "main_item_code", None))
                candidates = maps.get("by_pair_index", {}).get(pair_key, [])
                if len(candidates) == 1:
                    src = candidates[0]

        if not src:
            continue

        updated_values = {}
        for fieldname in custom_fields:
            if hasattr(row, fieldname):
                value = getattr(src, fieldname, None)
                if value not in (None, ""):
                    setattr(row, fieldname, value)
                    updated_values[fieldname] = value

        if persist_children and updated_values:
            try:
                row.db_update()
            except Exception:
                try:
                    for fname, fval in updated_values.items():
                        frappe.db.set_value(row.doctype, row.name, fname, fval, update_modified=False)
                except Exception:
                    pass


def before_save(doc, method):
    # Populate in memory so values are present on draft
    _populate_supplied_custom_fields(doc, persist_children=False)


def after_save(doc, method):
    # Persist child values in case mapped doc was already saved
    _populate_supplied_custom_fields(doc, persist_children=True)