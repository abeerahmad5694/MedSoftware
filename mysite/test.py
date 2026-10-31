

import sys, re, pathlib

def fix_content(text):
    # 1. Fix Django broken: ="" ="
    # Example: {% if config.pos.default_page_size="" ="thermal_80" %}
    # -> {% if config.pos.default_page_size == "thermal_80" %}
    text = re.sub(r'=\s*""\s*=\s*"', '== "', text)
    text = re.sub(r'=\s*""\s*=\s*'', "== '", text)
    
    # 2. Fix Django missing space before == :  default_page== "A5"  -> default_page == "A5"
    # Only inside {% if ... %} blocks, but safe globally for == 
    text = re.sub(r'(\w)==\s*"', r'\1 == "', text)
    text = re.sub(r"(\w)==\s*'", r"\1 == '", text)
    text = re.sub(r'"==', '" ==', text)  # just in case
    
    # 3. Fix JS broken ===  ->  Antigravity makes "== =" into "== ="
    # a) == =  -> ===
    # Examples:
    #   typeof x == = 'string'  -> typeof x === 'string'
    #   opt.value == =f.field_name -> opt.value === f.field_name
    text = re.sub(r'==\s*=\s*', '=== ', text)
    
    # 4. Fix missing space after ===  :  ===f  -> === f
    text = re.sub(r'===([a-zA-Z_\$])', r'=== \1', text)
    text = re.sub(r'==([a-zA-Z_\$])', r'== \1', text)
    
    # 5. Fix double equals still broken like "== ="
    text = text.replace('== =', '===')
    
    # 6. Specific: company.id="" ="c.id" is rare case but same as #1
    # Already fixed by #1
    
    return text

if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else "company_config.html"
    p = pathlib.Path(file_arg)
    if not p.exists():
        # Try to find in current dir
        print(f"File not found: {p}")
        sys.exit(1)
    original = p.read_text(encoding='utf-8')
    fixed = fix_content(original)
    
    # Count fixes
    changes = 0
    if original != fixed:
        p.write_text(fixed, encoding='utf-8')
        print(f"Fixed: {p}")
        # Show diff summary
        import difflib
        for line in difflib.unified_diff(original.splitlines(), fixed.splitlines(), lineterm=''):
            if line.startswith('+') or line.startswith('-'):
                if '==' in line or '===' in line:
                    print(line[:200])
        print("\nDone. Now reload page with Ctrl+F5. Tabs and category combo will work.")
    else:
        print("No changes needed - file already clean")

# import re, pathlib
# # CHANGE THIS to your actual file location
# p = pathlib.Path("apps/configuration/templates/configuration/company_config.html")
# # or if your structure is templates/configuration/company_config.html
# if not p.exists():
#     p = pathlib.Path("templates/configuration/company_config.html")
# if not p.exists():
#     # try find recursively
#     for f in pathlib.Path(".").rglob("company_config.html"):
#         p = f
#         break

# print(f"Fixing {p}")
# text = p.read_text(encoding="utf-8", errors="ignore")

# # === CORE FIX ===
# # Antigravity breaks == into ="" ="
# text = text.replace('="" ="', ' == ')
# text = text.replace('= "" =', ' == ')
# text = text.replace('=""=""', ' == ')
# text = text.replace('==""', ' == ')
# text = text.replace('""=', ' == ')

# # Normalize any == without spaces
# text = re.sub(r'\s*==\s*', ' == ', text)

# # Fix double spaces inside {% if %}
# text = re.sub(r'{%\s+if\s+', '{% if ', text)
# text = re.sub(r'\s{2,}selected', ' selected', text)

# p.write_text(text, encoding="utf-8")
# print("DONE - All {% if a == \"b\" %} fixed")
# print("Check with: git diff", p)