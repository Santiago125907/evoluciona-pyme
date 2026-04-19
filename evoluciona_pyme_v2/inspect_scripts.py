import json

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/server_script.json', 'r') as f:
    scripts = json.load(f)

for s in scripts:
    ref_dt = s.get('reference_doctype', 'API/Other')
    hook = s.get('doctype_event', '') or s.get('script_type', '')
    name = s.get('name')
    print(f"[{s.get('script_type')}] {name} on {ref_dt} - {hook}")
