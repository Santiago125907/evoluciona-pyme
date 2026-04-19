import json

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/web_page.json', 'r') as f:
    web = json.load(f)
with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/workspace.json', 'r') as f:
    ws = json.load(f)

for w in web:
    print(f"Web Page: {w.get('name')}")
for w in ws:
    print(f"Workspace: {w.get('name')}")
