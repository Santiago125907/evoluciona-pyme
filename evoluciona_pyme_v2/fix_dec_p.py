import re

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/scratch/scripts/server_Declaracion_Mensual_Before_Save.py', 'r') as f:
    script = f.read()

py_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/doctype/declaracion_mensual/declaracion_mensual.py'

content = """# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Declaracion_Mensual(Document):
\tdef before_save(self):
"""

for line in script.split('\n'):
    if line.startswith('def ') or line.startswith('#'): continue
    if line.strip() == 'actualizar_estado_declaracion(doc)':
        content += "\t\tself.actualizar_estado_declaracion()\n"
        continue
    if line.strip() == 'calcular_vencimientos_impuestos(doc)':
        content += "\t\tself.calcular_vencimientos_impuestos()\n"
        continue
    if line.strip() == 'if not doc.is_new():':
        content += "\t\tif not self.is_new():\n"
        continue
    if line.strip() == 'crear_cobranza_si_corresponde(doc)':
        content += "\t\t\tself.crear_cobranza_si_corresponde()\n"
        continue
    if line.strip() == 'else:':
        content += "\t\telse:\n"
        continue
    if line.strip() == 'frappe.msgprint("ℹ️ Documento nuevo, no se crea cobranza aún", indicator=\'blue\')':
        content += "\t\t\tfrappe.msgprint(\"ℹ️ Documento nuevo, no se crea cobranza aún\", indicator='blue')\n"
        continue

# Now append the functions
method_body = False
for line in script.split('\n'):
    if line.startswith('def '):
        line = line.replace('(doc)', '(self)')
        content += "\n\t" + line + "\n"
        method_body = True
    elif method_body and line.startswith(' '):
        line = line.replace('doc.', 'self.').replace('doc,', 'self,').replace('(doc)', '(self)')
        line = re.sub(r'\bdoc\b', 'self', line)
        content += "\t" + line + "\n"
    elif not line.strip():
        content += "\n"
    else:
        method_body = False

with open(py_path, 'w') as f:
    f.write(content)
