"""
Phase 7 setup. Run ONCE from the project root:   python apply_phase7.py
Adds 2 lines to app/__init__.py (backup saved as __init___backup_before_phase7.py):
    from app.hardening import init_security
    init_security(app)          # just before "return app"
Safe to run twice.
"""
import re
import shutil

PATH = 'app/__init__.py'
text = open(PATH, encoding='utf-8', newline='').read()

if 'init_security' in text:
    print('SKIP: app/__init__.py already calls init_security')
else:
    shutil.copy(PATH, 'app/__init___backup_before_phase7.py')
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    match = None
    for match in re.finditer(r'^([ \t]+)return app[ \t]*$', text, re.M):
        pass                                          # take the LAST "return app" (the one in create_app)
    if not match:
        raise SystemExit('Could not find "return app". Add by hand inside create_app(), just before it:\n'
                         '    from app.hardening import init_security\n    init_security(app)')
    indent = match.group(1)
    block = f'{indent}from app.hardening import init_security\n{indent}init_security(app)\n\n'
    text = text[:match.start()] + block + text[match.start():]
    compile(text, PATH, 'exec')
    open(PATH, 'w', encoding='utf-8', newline='').write(text.replace('\n', nl))
    print('OK: init_security(app) added to app/__init__.py')
print('Next: python run.py  and walk through the checklist in PHASE7_AUDIT_REPORT.md')
