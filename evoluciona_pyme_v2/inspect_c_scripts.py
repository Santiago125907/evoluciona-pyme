import json

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/client_script.json', 'r') as f:
    scripts = json.load(f)

for s in scripts:
    ref_dt = s.get('dt', 'Other')
    print(f"[{s.get('module')}] {s.get('name')} on {ref_dt}")
