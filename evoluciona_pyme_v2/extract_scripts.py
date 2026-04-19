import json, os

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/server_script.json', 'r') as f:
    s_scripts = json.load(f)
with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/client_script.json', 'r') as f:
    c_scripts = json.load(f)

for s in s_scripts:
    name = s.get('name').replace(' ', '_').replace('/', '_')
    with open(f"/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/scratch/scripts/server_{name}.py", "w") as out:
        out.write(s.get('script', ''))

for c in c_scripts:
    name = c.get('name').replace(' ', '_').replace('/', '_')
    with open(f"/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/scratch/scripts/client_{name}.js", "w") as out:
        out.write(c.get('script', ''))
