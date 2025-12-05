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
        # If base name does not exist, use it
        if not frappe.db.exists("BOM", base_name):
            return base_name

        # Find the highest existing suffix for this base
        # FIXED: Use LIKE with proper pattern to match base name without suffix
        last = frappe.db.sql(
            """
            SELECT name FROM `tabBOM`
            WHERE name LIKE %s
            ORDER BY LENGTH(name) DESC, name DESC
            LIMIT 1
            """,
            f"{base_name}%",
            as_dict=True,
        )

        next_num = 1
        if last:
            try:
                # Extract suffix from the found BOM name
                bom_name = last[0].name
                
                # If the name is exactly the base name, start with 001
                if bom_name == base_name:
                    next_num = 1
                else:
                    # Try to extract suffix number
                    # Remove base_name from the beginning
                    suffix_part = bom_name[len(base_name):]
                    
                    # Remove leading hyphen if present
                    if suffix_part.startswith("-"):
                        suffix_part = suffix_part[1:]
                    
                    # Extract numeric part
                    import re
                    match = re.match(r'^(\d+)', suffix_part)
                    if match:
                        next_num = int(match.group(1)) + 1
            except Exception:
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