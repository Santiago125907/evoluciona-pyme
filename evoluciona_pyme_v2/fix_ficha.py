import os
import re

py_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/doctype/ficha_cliente/ficha_cliente.py'
src_path = '/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/scratch/scripts/server_Ficha_Cliente_-_Gestionar_Portal.py'

with open(src_path, 'r') as f:
    script_lines = f.readlines()

new_content = """# Copyright (c) 2026, Santiago Romero and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Ficha_Cliente(Document):
\tdef before_save(self):
"""

for line in script_lines:
    # replace doc with self
    line = line.replace('doc.', 'self.').replace('doc,', 'self,').replace('(doc)', '(self)')
    line = re.sub(r'\bdoc\b', 'self', line)
    new_content += "\t\t" + line

with open(py_path, 'w') as f:
    f.write(new_content)

print("Fixed ficha_cliente.py completely")
