import json
import os
import re

with open('/home/erpnext/erpnext-bench/apps/evoluciona_pyme/evoluciona_pyme/fixtures/server_script.json', 'r') as f:
    s_scripts = json.load(f)

for s in s_scripts:
    if s.get('script_type') == 'DocType Event' and s.get('name') != 'Borrador_F29':
        dt = s.get('reference_doctype')
        event = s.get('doctype_event')
        script = s.get('script')
        
        if not dt or not script: continue
        
        # map event to python method name
        event_map = {
            'Before Save': 'before_save',
            'Before Insert': 'before_insert',
            'After Save': 'on_update',
            'After Insert': 'after_insert',
            'Before Submit': 'before_submit',
            'On Submit': 'on_submit',
            'Before Cancel': 'before_cancel',
            'On Cancel': 'on_cancel',
        }
        method_name = event_map.get(event)
        if not method_name:
            print(f"Unknown event {event} for {dt}")
            continue
            
        dt_slug = dt.lower().replace(' ', '_')
        py_path = f"/home/erpnext/erpnext-bench/apps/evoluciona_pyme_v2/evoluciona_pyme_v2/evoluciona_pyme_v2/doctype/{dt_slug}/{dt_slug}.py"
        
        if os.path.exists(py_path):
            with open(py_path, 'r') as f:
                content = f.read()
                
            # very basic replacement: replace `pass` with the method
            # convert doc. to self.
            script_body = ""
            for line in script.split('\n'):
                line = line.replace('doc.', 'self.').replace('doc,', 'self,').replace('(doc)', '(self)')
                line = re.sub(r'\bdoc\b', 'self', line) # replace standalone doc with self
                script_body += f"\t\t{line}\n"
                
            method_def = f"\tdef {method_name}(self):\n{script_body}"
            
            if "pass" in content:
                content = content.replace("pass", method_def)
            else:
                content += f"\n{method_def}"
                
            with open(py_path, 'w') as f:
                f.write(content)
            
            print(f"Injected {method_name} into {dt_slug}.py")
        else:
            print(f"Warning: PY path not found for {dt}: {py_path}")
            
