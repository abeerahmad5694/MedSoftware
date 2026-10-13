"""
invoice_designer.services.renderer
------------------------------------
The one and only rendering engine:

    Template Configuration + Document Data = HTML

Performance principles (all O(n) or O(1), never O(n²)):
- Every field/column/totals value is fully resolved in Python BEFORE
  the template runs. The template only loops over already-resolved dicts.
- Configuration is merged with defaults once per render, not per field.
- Zero-value filtering is done here so the template stays dumb.
- Column format strings are evaluated here using a simple str.format_map.

Rendering priority for a field's VALUE (requirement #2):
    1. document_data["field_overrides"][field_key]   (per-print override)
    2. field_config["custom_value"]                   (template-level override)
    3. document_data value at the field's data_source path (the real DB value)

New field config options:
    prefix          : string prepended to the resolved value (e.g. "INV-")
    suffix          : string appended to the resolved value
    hide_if_zero    : bool — suppress this total/field row when value is 0
    format_string   : for item columns — a Python format string that can
                      reference any item field key with {field_name} syntax,
                      OR the short drag-and-drop column alias (format_key).
                      Both syntaxes work and both work even when the column
                      is disabled/hidden in the current template layout.
                      e.g. "{product_name} ({discount_percent}%)"   ← internal keys
                           "{Product} ({Disc}%)"                    ← short aliases
                           "{Product} x{Qty} @ {Rate}"             ← mixed OK too
"""

from copy import deepcopy

from django.core.cache import cache
from django.template.loader import render_to_string

from apps.invoice_designer.schema import (
    FIELD_REGISTRY,
    ITEM_COLUMN_REGISTRY,
    TOTALS_REGISTRY,
    URDU_COLUMN_LABELS,
    default_configuration_for,
    get_invoice_language_for_page_type,
    is_urdu_page_type,
    is_bilingual_page_type,
    resolve_style,
    style_dict_to_css,
)

TEMPLATE_NAME = "invoice_designer/document_template.html"
CONFIGURATION_CACHE_TIMEOUT_SECONDS = 300

# Fields where zero IS meaningful and should never be hidden
_ZERO_ALWAYS_VISIBLE = {"net_total", "subtotal"}

# ---------------------------------------------------------------------------
# Built ONCE at import time from ITEM_COLUMN_REGISTRY (O(registry_size)).
# Maps every format_key alias → internal field key, e.g.:
#   "Product"  → "product_name"
#   "Disc"     → "discount_percent"
#   "Qty"      → "quantity"
# This lets users write {Product} or {product_name} in format_string — both work,
# and it works even if that column is disabled/hidden in the current template.
# ---------------------------------------------------------------------------
_FORMAT_KEY_TO_FIELD: dict[str, str] = {
    entry["format_key"]: field_key
    for field_key, entry in ITEM_COLUMN_REGISTRY.items()
    if entry.get("format_key")
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge `override` onto `base` without mutating either argument."""
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_by_path(data: dict, path: str):
    """'company.name' -> data['company']['name'], tolerating missing keys."""
    if not path:
        return None
    node = data
    for key in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _is_zero(value) -> bool:
    """Returns True if value represents a zero / empty / N/A quantity."""
    if value is None or value == "" or value == "N/A":
        return True
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def _resolve_field_value(field_key: str, field_config: dict, registry_entry: dict, document_data: dict):
    """Priority 1 -> 2 -> 3, as documented at module level."""
    overrides = (document_data or {}).get("field_overrides") or {}
    if field_key in overrides:
        return overrides[field_key]

    custom_value = field_config.get("custom_value")
    if custom_value not in (None, ""):
        return custom_value

    if registry_entry.get("field_type") == "static_text":
        return registry_entry.get("static_text", "")

    data_source = registry_entry.get("data_source")
    if data_source:
        value = _get_by_path(document_data or {}, data_source)
        if value not in (None, ""):
            return value

    return ""


def _apply_prefix_suffix(value, field_config: dict) -> str:
    """Prepend/append prefix and suffix defined in the field config."""
    prefix = field_config.get("prefix") or ""
    suffix = field_config.get("suffix") or ""
    if prefix or suffix:
        return f"{prefix}{value}{suffix}"
    return value


def _resolve_field_style_css(field_config: dict) -> str:
    style_name = field_config.get("style", "normal")
    overrides = field_config.get("style_overrides")
    return style_dict_to_css(resolve_style(style_name, overrides))


def _to_number(value, default=0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_css_unit(value):
    if not value:
        return ""
    val_str = str(value).strip()
    if val_str.isdigit():
        return f"{val_str}px"
    return val_str


def _format_number(value):
    """
    Format numeric values (max 2 decimal places, stripped trailing zeros).
    Passes strings/non-numbers through unchanged.
    Strips commas before parsing so '1,200.00' is handled correctly.
    """
    if value is None or value == "":
        return value
    if isinstance(value, str):
        clean_value = value.replace(",", "")
        try:
            f = float(clean_value)
        except ValueError:
            return value
    else:
        try:
            f = float(value)
        except (TypeError, ValueError):
            return value
            
    rounded = round(f, 2)
    return f"{rounded:.2f}".rstrip("0").rstrip(".")

class DocumentRenderer:
    """Stateless. Safe to instantiate once per request or reuse globally."""

    def build_complete_configuration(self, configuration: dict) -> dict:
        document_type = configuration.get("document_type")
        page_type = configuration.get("page_type")
        defaults = default_configuration_for(document_type, page_type)
        return _deep_merge(defaults, configuration)

    # ------------------------------------------------------------- fields

    def _resolve_field_section(self, section_key: str, section_config: dict, document_data: dict) -> list:
        """[{field, visible, style_css, value, type, label}] for one section."""
        resolved = []
        
        # Check if customer section should be excluded based on exclude_accounts
        if section_key == "customer" and section_config.get("exclude_accounts"):
            excluded = [acc.strip().lower() for acc in section_config["exclude_accounts"].split(",") if acc.strip()]
            if excluded:
                customer_data = document_data.get("customer", {})
                c_name = str(customer_data.get("name", "")).strip().lower()
                c_code = str(customer_data.get("account_code", "")).strip().lower()
                if c_name in excluded or c_code in excluded:
                    return []

        for field_config in section_config.get("fields", []):
            field_key = field_config.get("field")
            if not field_config.get("visible", True):
                continue

            registry_entry = FIELD_REGISTRY.get(field_key)
            if registry_entry is None:
                registry_entry = {"field_type": "text", "data_source": None}

            value = _resolve_field_value(field_key, field_config, registry_entry, document_data)
            
            value_ur = ""
            data_source = registry_entry.get("data_source")
            if data_source:
                value_ur = _get_by_path(document_data or {}, data_source + "_ur") or ""

            value = _apply_prefix_suffix(value, field_config)
            if value_ur:
                value_ur = _apply_prefix_suffix(value_ur, field_config)

            # Auto-hide empty text fields (e.g., if customer name or address is blank)
            if value == "" and value_ur == "" and registry_entry.get("field_type") != "image":
                continue

            resolved.append({
                "field": field_key,
                "label": field_config.get("label") or registry_entry.get("label", field_key),
                "value": value,
                "value_ur": value_ur,
                "style_css": _resolve_field_style_css(field_config),
                "type": registry_entry.get("field_type", "text"),
                "logo_width": _to_css_unit(field_config.get("logo_width") or field_config.get("style_overrides", {}).get("width")),
                "logo_height": _to_css_unit(field_config.get("logo_height")),
            })
        return resolved

    def _resolve_item_columns(self, items_config: dict, all_items: list) -> list:
        """
        Returns visible columns. Columns whose values are ALL zero/empty
        across every item row are automatically hidden (hide_if_zero logic).
        """
        columns = [c for c in items_config.get("columns", []) if c.get("visible", True)]
        columns.sort(key=lambda c: c.get("order", 0))
        resolved = []
        for column in columns:
            field_key = column.get("field")
            registry_entry = ITEM_COLUMN_REGISTRY.get(field_key, {})

            # Auto-hide column if all values are zero (unless explicitly kept)
            if not column.get("always_show") and all_items:
                all_zero = all(
                    _is_zero(
                        row.get(field_key, "") if isinstance(row, dict)
                        else getattr(row, field_key, "")
                    )
                    for row in all_items
                )
                if all_zero:
                    continue

            resolved.append({
                "field": field_key,
                "label": column.get("label") or registry_entry.get("label", field_key),
                "default_label": registry_entry.get("label", field_key),
                "width": column.get("width") or registry_entry.get("default_width", "auto"),
                "style_css": _resolve_field_style_css(column),
                "format_string": column.get("format_string") or None,  # e.g. "{product_name} ({discount_percent}%)"
            })
        return resolved

    def _resolve_item_rows(self, visible_columns: list, document_data: dict) -> list:
        """
        Build row data. If a column has a format_string, evaluate it using
        the full item dict so multiple fields can be merged into one cell.

        Performance: O(items × columns) — exactly one pass, no nested scans.

        format_string supports two equivalent syntaxes (both resolved here):
          • Internal key:  "{product_name} ({discount_percent}%)"
          • Short alias:   "{Product} ({Disc}%)"
        Both work regardless of whether that column is visible or not.
        """
        rows = (document_data or {}).get("items", []) or []
        result = []
        for row in rows:
            # Build the canonical key → value dict once per row  O(fields)
            raw_dict = row if isinstance(row, dict) else {
                f.attname: getattr(row, f.attname, "")
                for f in row._meta.fields
            }
            # Pre-format all numeric values in the row so format strings get clean numbers
            row_dict = {
                k: _format_number(v)
                for k, v in raw_dict.items()
            }

            # Extend with format_key aliases so {Product}, {Disc}, {Qty} etc.
            # resolve correctly — even for disabled/hidden columns.  O(aliases)
            alias_dict = {
                alias: row_dict.get(field_key, "")
                for alias, field_key in _FORMAT_KEY_TO_FIELD.items()
            }
            # Merge: internal keys win over aliases on collision
            fmt_ctx = {**alias_dict, **{k: (v if v is not None else "") for k, v in row_dict.items()}}

            cells = []
            for column in visible_columns:
                fmt = column.get("format_string")
                if fmt:
                    try:
                        cell_val = fmt.format_map(fmt_ctx)
                    except (KeyError, ValueError):
                        cell_val = row_dict.get(column["field"], "")
                else:
                    cell_val = row_dict.get(column["field"], "")
                cells.append({
                    "value": cell_val,
                    "style_css": column.get("style_css", "")
                })
            result.append(cells)
        return result

    def _resolve_totals(self, totals_config: dict, document_data: dict) -> list:
        """
        Ordered, visible totals fields with their computed values.
        Fields whose value is 0/empty are hidden unless they are in
        _ZERO_ALWAYS_VISIBLE or the field config has hide_if_zero=False.
        """
        totals_data = dict((document_data or {}).get("totals") or {})

        if "current_balance" not in totals_data and "previous_balance" in totals_data:
            received = (
                _to_number(totals_data.get("cash_received"))
                + _to_number(totals_data.get("bank_received"))
            )
            totals_data["current_balance"] = round(
                _to_number(totals_data.get("previous_balance"))
                + _to_number(totals_data.get("net_total"))
                - received,
                2,
            )

        fields = sorted(
            (f for f in totals_config.get("fields", []) if f.get("visible", True)),
            key=lambda f: f.get("order", 0),
        )

        resolved = []
        for field_config in fields:
            key = field_config.get("field")
            registry_entry = TOTALS_REGISTRY.get(key, {})
            data_source = registry_entry.get("data_source", "")
            sub_key = data_source.split(".", 1)[1] if "." in data_source else key
            value = totals_data.get(sub_key, 0)

            # Hide zero values unless the field is always-visible or explicitly kept
            hide_if_zero = field_config.get("hide_if_zero", True)
            if hide_if_zero and key not in _ZERO_ALWAYS_VISIBLE and _is_zero(value):
                continue

            resolved.append({
                "field": key,
                "label": field_config.get("label") or registry_entry.get("label", key),
                "value": _format_number(value),
                "style_css": _resolve_field_style_css(field_config),
            })
        return resolved

    # ------------------------------------------------------------- render

    def render(self, configuration: dict, document_data: dict) -> str:
        complete_configuration = self.build_complete_configuration(configuration)
        document_data = document_data or {}
        sections = complete_configuration["sections"]

        # Determine invoice language (urdu | bilingual | english)
        page_type = complete_configuration.get("page_type", "")
        invoice_language = (
            complete_configuration.get("invoice_language")
            or get_invoice_language_for_page_type(page_type)
        )
        is_urdu = invoice_language == "urdu" or is_urdu_page_type(page_type)
        is_bilingual = invoice_language == "bilingual" or is_bilingual_page_type(page_type)
        has_urdu = is_urdu or is_bilingual

        # Urdu column-label overrides (stored in config, fallback to module-level dict)
        column_labels_ur = complete_configuration.get("column_labels_ur") or (URDU_COLUMN_LABELS if has_urdu else {})

        context = {
            "page": complete_configuration["page"],
            "document_type": complete_configuration.get("document_type"),
            "page_type": page_type,
            "default_font_family": complete_configuration["styles"].get("default_font_family", "Arial"),
            "default_font_size": complete_configuration["styles"].get("default_font_size", 12),
            # Urdu / language context
            "invoice_language": invoice_language,
            "is_urdu": is_urdu,
            "is_bilingual": is_bilingual,
            "has_urdu": has_urdu,
            "column_labels_ur": column_labels_ur,
        }

        if complete_configuration.get("document_type") == "barcode_label":
            context["barcode"] = sections.get("barcode", {})
            context["labels"] = document_data.get("labels", [])
            return render_to_string("invoice_designer/barcode_template.html", context)

        context["header_section"] = {
            "visible": sections["header"].get("visible", True),
            "fields": self._resolve_field_section("header", sections["header"], document_data),
        }
        context["customer_section"] = {
            "visible": sections["customer"].get("visible", True),
            "fields": self._resolve_field_section("customer", sections["customer"], document_data),
        }
        context["footer_section"] = {
            "visible": sections["footer"].get("visible", True),
            "fields": self._resolve_field_section("footer", sections["footer"], document_data),
        }

        # Pass raw items to column resolver so it can detect all-zero columns
        raw_items = document_data.get("items", []) or []
        visible_columns = self._resolve_item_columns(sections["items"], raw_items)
        plain_rows = self._resolve_item_rows(visible_columns, document_data)

        # Build rows_with_urdu for Urdu/Bilingual templates.
        # Each entry: {cells: [{"value": cell_val, "field": col_field}, ...], product_name_ur: str}
        rows_with_urdu = []
        for row_idx, row_item in enumerate(raw_items):
            raw_dict = row_item if isinstance(row_item, dict) else {}
            pname_ur = raw_dict.get("product_name_ur", "") or ""
            plain_cells = plain_rows[row_idx] if row_idx < len(plain_rows) else []
            
            cells_with_meta = []
            for c_idx, cell in enumerate(plain_cells):
                field_id = visible_columns[c_idx]["field"] if c_idx < len(visible_columns) else ""
                cells_with_meta.append({"value": cell["value"], "field": field_id, "style_css": cell["style_css"]})

            rows_with_urdu.append({
                "cells": cells_with_meta,
                "product_name_ur": pname_ur,
            })

        context["items_section"] = {
            "visible": sections["items"].get("visible", True),
            "columns": visible_columns,
            "rows": plain_rows,
            "rows_with_urdu": rows_with_urdu,
            "table_borders": sections["items"].get("table_borders", False),
        }

        context["totals_section"] = {
            "visible": sections["totals"].get("visible", True),
            "fields": self._resolve_totals(sections["totals"], document_data),
        }

        return render_to_string(TEMPLATE_NAME, context)



class TemplateConfigurationCache:
    """
    Thin cache wrapper around TemplateConfiguration lookups.
    The PRD explicitly asks to "cache template configuration" for
    performance — this is the single place that happens, so cache
    invalidation only ever needs to be reasoned about here.
    """

    KEY_FORMAT = "invoice_designer:template_configuration:{document_type}:{page_type}:{name}"

    @classmethod
    def key(cls, document_type, page_type, name="Default"):
        return cls.KEY_FORMAT.format(document_type=document_type, page_type=page_type, name=name)

    @classmethod
    def get_or_build(cls, document_type, page_type, name="Default"):
        cache_key = cls.key(document_type, page_type, name)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from ..models import TemplateConfiguration  # local import avoids app-loading races

        try:
            template = TemplateConfiguration.objects.get(
                document_type=document_type, page_type=page_type, name=name
            )
            configuration = template.configuration
        except TemplateConfiguration.DoesNotExist:
            configuration = default_configuration_for(document_type, page_type)

        cache.set(cache_key, configuration, CONFIGURATION_CACHE_TIMEOUT_SECONDS)
        return configuration

    @classmethod
    def invalidate(cls, document_type, page_type, name="Default"):
        cache.delete(cls.key(document_type, page_type, name))
