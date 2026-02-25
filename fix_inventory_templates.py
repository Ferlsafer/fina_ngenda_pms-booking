#!/usr/bin/env python3
"""Fix inventory template syntax errors"""
import os
import re

def fix_template_syntax():
    template_dir = "/home/bytehustla/hms_finale-main/app/templates/hms/inventory"
    
    files_to_fix = [
        "suppliers.html",
        "purchase_order_form.html", 
        "item_form.html",
        "purchase_orders.html",
        "view_item.html"
    ]
    
    for filename in files_to_fix:
        filepath = os.path.join(template_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Fix url_for syntax: change {{ url_for('route') }} to {{ url_for('route') }}
            original_content = content
            content = re.sub(r'\{\{\s*url_for\(([^}]+)\)\s*\}\}', r'{{ url_for(\1) }}', content)
            
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Fixed {filename}")
            else:
                print(f"No issues found in {filename}")

if __name__ == '__main__':
    fix_template_syntax()
    print("Template syntax fix complete!")
