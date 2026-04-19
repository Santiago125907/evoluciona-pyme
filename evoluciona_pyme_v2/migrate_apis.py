import json
import os
import re

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/server_script.json', 'r') as f:
    s_scripts = json.load(f)

api_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/api.py'

with open(api_path, 'w') as api_file:
    api_file.write("import frappe\n\n")
    
    for s in s_scripts:
        if s.get('script_type') == 'API':
            name = s.get('api_method') or s.get('name').lower().replace(' ', '_').replace('-', '_')
            name = re.sub(r'[^a-zA-Z0-9_]', '', name)
            guest = s.get('allow_guest', 0)
            script = s.get('script')
            
            api_file.write(f"@frappe.whitelist(allow_guest={bool(guest)})\n")
            api_file.write(f"def {name}(**kwargs):\n")
            
            for line in script.split('\n'):
                api_file.write(f"    {line}\n")
            api_file.write("\n\n")

print("APIs migrated to api.py")
