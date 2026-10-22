# Pattern Set Enhancements Documentation

## Steel Strong Valves - Mould Set Management
**Document Version:** 1.0  
**Module:** Generate Item / Mould Set Management  
**Applicable DocTypes:** `Pattern Set` (Parent), `Pattern Set Component` (Child Table)  
**System Reference:** Custom Item Attribute No. 4 (`FG-Bore`)

---

## 1. Overview & Objective

This document outlines the enhancements implemented for the **Pattern Set** workflow in the Steel Strong ERP system. These changes align the pattern set master records with engineering attributes configured in the **Item Generator Engine**, improve tooling identification precision, and introduce flexible remark tracking across both header and individual component items.

### Key Objectives:
1. **Bore Attribute Integration:** Sourced from Item Generator Attribute No. 4 (`FG-Bore`), reflecting Full Bore (`FB`), Reduced Bore (`RB`), and Standard Bore (`STD`) directly into the Pattern Set Name and Naming Series.
2. **Pattern Length Dropdown:** Classifying pattern tooling dimensions into `Short` or `Long` at the Pattern Set header level.
3. **Dual-Tier Remark Architecture:** Enabling comprehensive engineering and foundry remarks at both the Set level (header) and Component level (child table).

---

## 2. Detailed Enhancements

### 2.1 Bore Field & Dynamic Naming Integration

#### Background:
Previously, Pattern Sets were named using only `Type of Valve`, `Size`, and `Class`. This caused collisions and ambiguity between Full Bore and Reduced Bore casting patterns (e.g. 2" 150# Full Bore vs 2" 150# Reduced Bore). Furthermore, client-side options were previously pointing to Ends attributes, which caused incorrect options (like Flanged, Screwed) to appear in the Bore dropdown.

#### Changes Implemented:
1. **DocType Schema (`Pattern Set`)**:
   - Field `bore` (Select) added to `Pattern Set`.
   - In List View: Enabled.
   - Standard Filter: Enabled.
   - Default Options: `\n-\nFB\nRB\nSTD`.

2. **Master Data Alignment (`FG-Bore`)**:
   - Mapped to **Custom Item Attribute No. 4**: `FG-Bore` (`component_name: "Bore"`).
   - Valid options from `logic_table`:
     | Code | Short Description | Long Description | Display Value | Description / Usage |
     | :--- | :--- | :--- | :--- | :--- |
     | `1` | `-` | `-` | `-` | Standard / Default (Omitted from name suffix) |
     | `F` | `FB` | `FB` | `FB` | Full Bore valve pattern tooling |
     | `R` | `RB` | `RB` | `RB` | Reduced Bore valve pattern tooling |
     | `S` | `STD` | `STD` | `STD` | Standard Bore valve pattern tooling |

3. **Pattern Set Name & Naming Series Generation**:
   - **Formula:** `[Type of Valve] [Size] [Class] [Bore]`
   - **Prefix & Series:**
     - **With Bore:** If `bore` is selected and not empty / not `"-"` (e.g. `FB`):  
       `pattern_set_name` = `GTV 2" 150# FB`  
       `naming_series` = `GTV 2" 150# FB-0001`
     - **Without Bore or '-' (Standard):** If `bore` is null, empty string, or `"-"`:  
       `pattern_set_name` = `GTV 2" 150#`  
       `naming_series` = `GTV 2" 150#-0001`
   - **Auto-Incrementing Sequence:** Scans existing records matching `[Prefix]-%` and generates the next 4-digit sequential identifier (`0001`, `0002`, etc.).

4. **Script Updates**:
   - `pattern_set.js`: Corrected `load_pattern_set_attribute_options` from `["WIP-Ends", "FG-Ends", "Ends"]` to `["FG-Bore", "WIP-Bore", "Bore"]`.
   - `pattern_set.py`: Updated `autoname()`, `set_pattern_set_name()`, and `get_next_pattern_set_name()`.
   - `pattern_set_componen.py`: Updated `get_filter_options()` to query `FG-Bore`.

---

### 2.2 Pattern Length Selection Field

#### Background:
Foundry tooling equipment varies in overall pattern length (e.g., standard length vs compact length). A dedicated selection was required on the Pattern Set header.

#### Changes Implemented:
- **DocType Schema (`Pattern Set`)**:
  - **Fieldname:** `pattern_length`
  - **Fieldtype:** `Select`
  - **Label:** `Pattern Length`
  - **Options:** `Short\nLong`
  - **Mandatory:** `1` (`reqd`)
  - **In List View:** `1`
  - **In Standard Filter:** `1`
- Allows foundry managers and pattern store supervisors to filter and locate tooling based on length specifications directly from Desk.

---

### 2.3 Remark Tracking (Set Level & Item Level)

#### Background:
Pattern creation involves overall set fabrication remarks as well as individual component-specific machining allowances or pattern drawer details.

#### Changes Implemented:
1. **Set Level (Header - `Pattern Set`)**:
   - **Fieldname:** `remark`
   - **Fieldtype:** `Small Text`
   - **Label:** `Remark`
   - **Scope:** Overall set instructions, core box requirements, master drawing references, or pattern storage rack location.
2. **Item / Component Level (`Pattern Set Component`)**:
   - **Fieldname:** `remark`
   - **Fieldtype:** `Small Text`
   - **Label:** `Remark`
   - **Scope:** Line-item component instructions (e.g., specific draft angles, shrink allowances, match plate condition, pattern revision notes).

---

## 3. Summary of Modified Files

| File Path | Description of Changes |
| :--- | :--- |
| [`pattern_set.json`](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/mould_set_management/doctype/pattern_set/pattern_set.json) | Added `bore` (Select), `pattern_length` (Select), and `remark` (Small Text) fields to the doctype schema. |
| [`pattern_set.js`](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/mould_set_management/doctype/pattern_set/pattern_set.js) | Updated `load_pattern_set_attribute_options` to load `FG-Bore` instead of Ends; handled `"-"` option; updated client triggers for name preview. |
| [`pattern_set.py`](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/mould_set_management/doctype/pattern_set/pattern_set.py) | Added bore integration in `autoname()`, `set_pattern_set_name()`, and `get_next_pattern_set_name()` with auto-increment series generation. |
| [`pattern_set_component.json`](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/mould_set_management/doctype/pattern_set_component/pattern_set_component.json) | Added `remark` (Small Text) child field to capture item-level component notes. |
| [`pattern_set_componen.py`](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/mould_set_management/page/pattern_set_componen/pattern_set_componen.py) | Updated `get_filter_options()` to source `bores` from `FG-Bore`. |

---

## 4. Verification & Testing

1. **Bore Selection Verification:**
   - Navigating to Pattern Set form loads only valid bore options: `""`, `"-"`, `"FB"`, `"RB"`, `"STD"`.
   - Selecting `FB` produces: `[Valve Type] [Size] [Class] FB-0001`.
   - Selecting `-` or leaving blank produces: `[Valve Type] [Size] [Class]-0001`.
2. **Pattern Length Mandatory Check:**
   - Form cannot be saved without selecting either `Short` or `Long`.
3. **Remark Persistence Check:**
   - Saved values in Header Remark and Component Item Remarks persist across reload and submit.
