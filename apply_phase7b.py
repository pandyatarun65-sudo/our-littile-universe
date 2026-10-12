"""
Phase 7 part 2.  Run ONCE from the project root:   python apply_phase7b.py

  1. app/main/routes.py  -> memory edit/delete only for the person who created it (option B)
                            + csrf token check on add/edit/delete
  2. timeline.html       -> Edit/Delete buttons only on your own memories + csrf token in delete form
  3. memory_form.html    -> csrf token in the add/edit form
Backups: <file>_backup_before_phase7b.<ext>.   Safe to run twice.
(auth/routes.py, run.py and app/ratelimit.py come as ready files in the zip.)
"""
import re
import shutil

problems = []


def read(path):
    return open(path, encoding='utf-8', newline='').read()


def write(path, text):
    open(path, 'w', encoding='utf-8', newline='').write(text)


def backup(path):
    dot = path.rfind('.')
    shutil.copy(path, path[:dot] + '_backup_before_phase7b' + path[dot:])


def patch_main_routes(path='app/main/routes.py'):
    raw = read(path)
    if 'check_csrf' in raw:
        print('SKIP', path, '(already patched)')
        return
    nl = '\r\n' if '\r\n' in raw else '\n'
    text = raw.replace('\r\n', '\n')
    ok = True

    # imports
    old = 'from flask import Blueprint, render_template, redirect, url_for, request, flash\n'
    if old in text:
        text = text.replace(old, 'from flask import Blueprint, render_template, redirect, url_for, request, flash, abort\n', 1)
        text = text.replace('from app import db\n', 'from app import db\nfrom app.security import check_csrf\n', 1)
    else:
        ok = False

    def segment(src, start_marker, end_marker):
        a = src.find(start_marker)
        b = src.find(end_marker, a + 1)
        return a, (b if b != -1 else len(src))

    # add_memory: csrf check
    a, b = segment(text, 'def add_memory', '@main_bp.route(\'/memories/<int:memory_id>/edit\'')
    seg = text[a:b]
    new = seg.replace("    if request.method == 'POST':\n", "    if request.method == 'POST':\n        check_csrf()\n", 1)
    ok &= new != seg
    text = text[:a] + new + text[b:]

    # edit_memory: owner + csrf
    a, b = segment(text, 'def edit_memory', '@main_bp.route(\'/memories/<int:memory_id>/delete\'')
    seg = text[a:b]
    new = seg.replace(
        "    memory = Memory.query.get_or_404(memory_id)\n\n    if request.method == 'POST':\n",
        "    memory = Memory.query.get_or_404(memory_id)\n"
        "    if memory.created_by != current_user.id:      # Phase 7: only the creator may edit\n"
        "        abort(403)\n\n"
        "    if request.method == 'POST':\n        check_csrf()\n", 1)
    ok &= new != seg
    text = text[:a] + new + text[b:]

    # delete_memory: owner + csrf
    a, b = segment(text, 'def delete_memory', '@main_bp.route(\'/gallery\')')
    seg = text[a:b]
    new = seg.replace(
        "    memory = Memory.query.get_or_404(memory_id)\n",
        "    check_csrf()\n"
        "    memory = Memory.query.get_or_404(memory_id)\n"
        "    if memory.created_by != current_user.id:      # Phase 7: only the creator may delete\n"
        "        abort(403)\n", 1)
    ok &= new != seg
    text = text[:a] + new + text[b:]

    if not ok:
        print('!!', path, ': could not patch automatically (file differs from expected).')
        problems.append(path)
        return
    compile(text, path, 'exec')
    backup(path)
    write(path, text.replace('\n', nl))
    print('OK  ', path, ': creator-only edit/delete + csrf check')


def patch_template(path, edits):
    raw = read(path)
    if 'csrf_token' in raw and 'created_by == current_user.id' in raw:
        print('SKIP', path, '(already patched)')
        return
    nl = '\r\n' if '\r\n' in raw else '\n'
    text = raw.replace('\r\n', '\n')
    for pattern, repl in edits:
        new, n = re.subn(pattern, repl, text, count=1, flags=re.S)
        if n == 0:
            print('!!', path, ': could not find', pattern[:50])
            problems.append(path)
            return
        text = new
    backup(path)
    write(path, text.replace('\n', nl))
    print('OK  ', path)


TOKEN = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'

if __name__ == '__main__':
    patch_main_routes()

    # timeline: hide Edit/Delete unless it is my memory; add csrf token to the delete form
    patch_template('app/templates/timeline.html', [
        (r'([ \t]*)(<div class="memory-actions">)(.*?)(</form>\s*</div>)',
         lambda m: (m.group(1) + '{% if memory.created_by == current_user.id %}\n' + m.group(1) + m.group(2)
                    + re.sub(r'(<form [^>]*>)', lambda f: f.group(1) + '\n' + m.group(1) + '    ' + TOKEN, m.group(3), count=1)
                    + m.group(4) + '\n' + m.group(1) + '{% endif %}')),
    ])

    # memory form: csrf token
    patch_template('app/templates/memory_form.html', [
        (r'(<form method="POST" enctype="multipart/form-data" class="memory-form card">)',
         lambda m: m.group(1) + '\n        ' + TOKEN + '\n        <!-- created_by == current_user.id is enforced on the server -->'),
    ])
    print()
    print('Fix the "!!" lines above first.' if problems else 'Done. Now restart: python run.py')
