import re

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/scratch/scripts/server_Crear_Tareas_Mensuales.py', 'r') as f:
    script = f.read()

tasks_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/tasks.py'

with open(tasks_path, 'w') as f:
    f.write('''import frappe
from frappe.utils import add_months, getdate, formatdate, today

def crear_tareas_mensuales():
''')
    for line in script.split('\n'):
        # Indent everything
        line = line.replace('doc.', 'frappe.get_doc().') # Not relevant here as scheduler scripts don't have doc
        f.write('    ' + line + '\n')

print("Tasks migrated to tasks.py")
