def validate(doc, method):
    for row in doc.items:
        if not row.fg_reference_id and row.fg_item:
            for data in doc.items:
                if row.fg_item == data.item_code:
                    row.fg_reference_id = data.name
                    break
