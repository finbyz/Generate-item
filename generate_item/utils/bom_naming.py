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
            branch_abbr = branch_abbr
        
        # Clean the item code for naming (remove special characters)
        clean_item_code = item_code.upper()
        
        # Create the base name pattern
        if branch_abbr:
            base_name = f"BOM-{branch_abbr}-{clean_item_code}"
        else:
            base_name = f"BOM-{clean_item_code}"
        return base_name
        
    except Exception as e:
        frappe.log_error(
            "Custom BOM Naming Error",
            f"Failed to generate BOM name for item {item_code}: {str(e)}"
        )
        # Fallback to standard naming if custom naming fails
        return make_autoname("BOM-{item}-.####", "BOM")



def get_available_bom_name(base_name: str) -> str:
    """
    Ensure BOM name is unique. If `base_name` exists, append a zero-padded numeric suffix.

    Examples:
    - base exists: BOM-ABC-ITEM -> BOM-ABC-ITEM-001 (or next available)
    - base not exists: returns base
    """
    try:
        # First, check if the exact base_name exists
        if not frappe.db.exists("BOM", base_name):
            # Also check if any BOM exists with this base_name plus suffix
            existing_boms = frappe.db.sql(
                """
                SELECT name FROM `tabBOM`
                WHERE name LIKE %s
                ORDER BY name DESC
                """,
                f"{base_name}-%",
                as_dict=True,
            )
            
            if not existing_boms:
                return base_name
        
        # Find all existing BOMs with this base (with or without suffix)
        all_existing = frappe.db.sql(
            """
            SELECT name FROM `tabBOM`
            WHERE name = %s OR name LIKE %s
            ORDER BY name DESC
            """,
            (base_name, f"{base_name}-%"),
            as_dict=True,
        )

        # Find the highest suffix number
        max_suffix = 0
        
        for bom in all_existing:
            bom_name = bom.name
            
            # Check if it's the exact base name (no suffix)
            if bom_name == base_name:
                max_suffix = max(max_suffix, 1)
                continue
            
            # Try to extract suffix
            if bom_name.startswith(base_name + "-"):
                suffix_part = bom_name[len(base_name) + 1:]  # Remove base_name and "-"
                
                # Check if suffix is numeric
                if suffix_part.isdigit():
                    suffix_num = int(suffix_part)
                    max_suffix = max(max_suffix, suffix_num)
        
        # Calculate next available number
        next_num = max_suffix + 1
        
        # If we found a base without suffix (max_suffix would be 1), start from 001
        if max_suffix == 1:
            next_num = 1
        
        # Return next available suffixed name
        return f"{base_name}-{next_num:03d}"
        
    except Exception as e:
        frappe.log_error(
            "BOM Unique Naming Error",
            f"Failed to compute unique BOM name for base {base_name}: {str(e)}",
        )
        # As a last resort, let Frappe generate a unique hash-based name
        return make_autoname("BOM-.########", "BOM")

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
        branch_abbr = getattr(doc, 'branch_abbr', None) 
        
        # Clean item code
        clean_item_code = doc.item.upper()
        
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