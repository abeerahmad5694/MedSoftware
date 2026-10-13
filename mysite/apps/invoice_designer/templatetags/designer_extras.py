from django import template

from ..schema import resolve_style, style_dict_to_css

register = template.Library()


@register.filter
def field_style_css(style_ref):
    """{'style': 'tiny', 'style_overrides': {...}} -> inline CSS string.
    Used by barcode_template.html, which (unlike document_template.html)
    still resolves style refs at template-render time since its fields
    aren't pre-flattened by DocumentRenderer the way header/customer/
    items/totals/footer are."""
    if not style_ref:
        return ""
    return style_dict_to_css(resolve_style(style_ref.get("style", "normal"), style_ref.get("style_overrides")))


@register.filter
def field_visible(field_dict):
    return bool(field_dict) and field_dict.get("visible", True)


@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)


@register.filter(name="smart_number")
def smart_number(value):
    """
    Format a numeric value for invoice display:
      - Max 2 decimal places
      - Trailing zeros stripped: 15.00 -> "15", 1.5 -> "1.5", 1.55555 -> "1.55"
      - Non-numeric values (text, empty string, None) pass through unchanged.
    O(1) — no loops, pure arithmetic.
    """
    if value is None or value == "":
        return value
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value          # text cells (product name, notes, etc.) unchanged
    # Round to 2 dp, then strip trailing zeros via the 'g' format trick
    rounded = round(f, 2)
    # Use Decimal-style formatting: strip .00, keep .5, keep .55
    formatted = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return formatted
