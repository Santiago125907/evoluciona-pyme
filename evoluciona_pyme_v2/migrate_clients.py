import json
import os

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/client_script.json', 'r') as f:
    c_scripts = json.load(f)

for c in c_scripts:
    dt = c.get('dt')
    script = c.get('script')
    if not dt or not script: continue
    
    dt_slug = dt.lower().replace(' ', '_')
    js_path = f"/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/doctype/{dt_slug}/{dt_slug}.js"
    
    if os.path.exists(js_path):
        with open(js_path, 'a') as js_file:
            js_file.write(f"\n\n// Migrated from Client Script: {c.get('name')}\n")
            js_file.write(script)
            print(f"Appended client script {c.get('name')} to {js_path}")
    else:
        print(f"Warning: JS path not found for {dt}: {js_path}")
