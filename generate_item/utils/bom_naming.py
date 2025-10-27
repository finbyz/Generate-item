import frappe
from frappe.model.naming import make_autoname
from frappe.utils import cstr

# Cache to track used numbers in the current session
_session_number_cache = {}

def get_custom_bom_name(item_code, branch_abbr=None):
    """
    Generate custom BOM name in the format: BOM-{branch_abbr}-{item}-{###}
    
    Args:
        item_code (str): The item code for the BOM
        branch_abbr (str): Branch abbreviation (optional, will be fetched if not provided)
    
    Returns:
        str: Generated BOM name
    """
    try:
        # Get branch abbreviation if not provided
        if not branch_abbr:
            branch_abbr = get_branch_abbreviation_for_item(item_code)
        
        # Clean the item code for naming (remove special characters)
        clean_item_code = clean_item_code_for_naming(item_code)
        
        # Create the base name pattern
        if branch_abbr:
            base_pattern = f"BOM-{branch_abbr}-{clean_item_code}-"
        else:
            base_pattern = f"BOM-{clean_item_code}-"
        
        # Get the next sequence number for this pattern
        next_number = get_next_sequence_number(base_pattern)
        
        # Generate the final BOM name
        bom_name = f"{base_pattern}{next_number:03d}"
        
        # Cache this number to prevent duplicates in the same session
        _session_number_cache[bom_name] = True
        
        return bom_name
        
    except Exception as e:
        frappe.log_error(
            "Custom BOM Naming Error",
            f"Failed to generate BOM name for item {item_code}: {str(e)}"
        )
        # Fallback to standard naming if custom naming fails
        return make_autoname("BOM-{item}-.####", "BOM")

def get_next_sequence_number(base_pattern):
    """
    Get the next sequence number for a given base pattern by checking existing BOMs
    
    Args:
        base_pattern (str): The base pattern like "BOM-RA-VALVE_001-"
    
    Returns:
        int: Next sequence number
    """
    try:
        # Extract item code from the base pattern
        # Pattern: BOM-{branch_abbr}-{item}- -> we need the item part
        pattern_parts = base_pattern.split('-')
        if len(pattern_parts) >= 3:
            item_code = pattern_parts[2]  # The item code part
        else:
            item_code = pattern_parts[1] if len(pattern_parts) >= 2 else ""
        
        # Query existing BOMs that match this pattern (custom pattern)
        existing_boms_custom = frappe.db.sql("""
            SELECT name 
            FROM `tabBOM` 
            WHERE name LIKE %s
            ORDER BY name DESC
            LIMIT 1
        """, f"{base_pattern}%", as_dict=True)
        
        # Also check for existing BOMs with standard pattern for the same item
        existing_boms_standard = frappe.db.sql("""
            SELECT name 
            FROM `tabBOM` 
            WHERE name LIKE %s
            ORDER BY name DESC
            LIMIT 1
        """, f"BOM-{item_code}-%", as_dict=True)
        
        # Get the highest number from both patterns
        max_number = 0
        
        # Check custom pattern BOMs
        if existing_boms_custom:
            last_name = existing_boms_custom[0].name
            number_part = last_name.split('-')[-1]
            try:
                number = int(number_part)
                max_number = max(max_number, number)
            except ValueError:
                pass
        
        # Check standard pattern BOMs
        if existing_boms_standard:
            last_name = existing_boms_standard[0].name
            number_part = last_name.split('-')[-1]
            try:
                number = int(number_part)
                max_number = max(max_number, number)
            except ValueError:
                pass
        
        # Check session cache for numbers used in this session
        for cached_name in _session_number_cache:
            if cached_name.startswith(base_pattern):
                try:
                    cached_number = int(cached_name.split('-')[-1])
                    max_number = max(max_number, cached_number)
                except ValueError:
                    pass
        
        # Return next number
        return max_number + 1 if max_number > 0 else 1
            
    except Exception as e:
        frappe.log_error(
            "Sequence Number Error",
            f"Failed to get next sequence number for pattern {base_pattern}: {str(e)}"
        )
        return 1

def get_branch_abbreviation_for_item(item_code):
    """
    Get branch abbreviation for an item by looking up related documents
    
    Args:
        item_code (str): The item code
    
    Returns:
        str: Branch abbreviation or empty string
    """
    try:
        # First try to get from Item's default BOM if it exists
        default_bom = frappe.get_cached_value("Item", item_code, "default_bom")
        if default_bom:
            branch_abbr = frappe.get_cached_value("BOM", default_bom, "branch_abbr")
            if branch_abbr:
                return branch_abbr
        
        # Try to get from Production Plan context if available
        # This is useful when BOMs are created from Production Plans
        production_plan = frappe.local.get("current_production_plan")
        if production_plan:
            branch_abbr = frappe.get_cached_value("Production Plan", production_plan, "branch_abbr")
            if branch_abbr:
                return branch_abbr
        
        # Try to get from Sales Order context if available
        sales_order = frappe.local.get("current_sales_order")
        if sales_order:
            branch_abbr = frappe.get_cached_value("Sales Order", sales_order, "branch_abbr")
            if branch_abbr:
                return branch_abbr
        
        # Default branch abbreviation mapping
        branch_abbr_map = {
            'Rabale': 'RA',
            'Nandikoor': 'NA',
            'Sanand': 'SA'
        }
        
        # Try to get branch from Item's warehouse or other sources
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"item_code": item_code},
            fields=["branch"],
            limit=1
        )
        
        if warehouses and warehouses[0].branch:
            return branch_abbr_map.get(warehouses[0].branch, '')
        
        # Return empty string if no branch found
        return ''
        
    except Exception as e:
        frappe.log_error(
            "Branch Abbreviation Lookup Error",
            f"Failed to get branch abbreviation for item {item_code}: {str(e)}"
        )
        return ''

def clean_item_code_for_naming(item_code):
    """
    Clean item code for use in naming (remove special characters, limit length)
    
    Args:
        item_code (str): Original item code
    
    Returns:
        str: Cleaned item code
    """
    if not item_code:
        return "ITEM"
    
    # Remove special characters and replace with underscores
    import re
    clean_code = re.sub(r'[^a-zA-Z0-9]', '_', item_code)
    
    # Remove multiple consecutive underscores
    clean_code = re.sub(r'_+', '_', clean_code)
    
    # Remove leading/trailing underscores
    clean_code = clean_code.strip('_')
    
    # Limit length to 20 characters for naming
    if len(clean_code) > 20:
        clean_code = clean_code[:20]
    
    # Ensure we have something to work with
    if not clean_code:
        clean_code = "ITEM"
    
    return clean_code.upper()

def set_bom_naming_series(doc):
    """
    Set the naming series for a BOM document based on branch and item
    
    Args:
        doc: BOM document
    """
    try:
        if not doc.item:
            return
        
        # Get branch abbreviation
        branch_abbr = getattr(doc, 'branch_abbr', None) or get_branch_abbreviation_for_item(doc.item)
        
        # Clean item code
        clean_item_code = clean_item_code_for_naming(doc.item)
        
        # Create custom naming pattern
        if branch_abbr:
            naming_pattern = f"BOM-{branch_abbr}-{clean_item_code}-.###"
        else:
            naming_pattern = f"BOM-{clean_item_code}-.###"
        
        # Set the naming series
        doc.naming_series = naming_pattern
        
        frappe.log_error(
            "BOM Naming Series Set",
            f"Set naming series {naming_pattern} for BOM with item {doc.item}, branch_abbr: {branch_abbr}"
        )
        
    except Exception as e:
        frappe.log_error(
            "BOM Naming Series Error",
            f"Failed to set naming series for BOM: {str(e)}"
        )