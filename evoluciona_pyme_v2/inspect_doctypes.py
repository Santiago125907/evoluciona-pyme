import json

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/doctype.json', 'r') as f:
    data = json.load(f)

for dt in data:
    if 'name' in dt:
        print(f"DocType: {dt['name']}, Module: {dt.get('module')}, Custom: {dt.get('custom')}")
