"""
Phase 7 part 3.  Run ONCE from the project root:   python apply_phase7c.py

 A) LOGOUT: base.html "Exit" link becomes a small POST form (with csrf token)
 B) LETTER CSRF: every <form method="post"> in app/templates/**  gets the hidden csrf_token field
    (letters, open-when, secret box, login, ... all at once). The server now checks the token on
    EVERY POST (app/hardening.py), so this step must succeed for every form - the script verifies it.
 C) TIMEZONE: "today" comes from app/timeutil.py (IST by default) in models, dashboard, daily question,
    special dates, locked-surprise count and notifications.
Each changed file is first copied to phase7c_backups/ (same path).  Safe to run twice.
"""
import os
import re
import shutil
import sys

problems = []
TOKEN_INPUT = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
FORM_RE = re.compile(r'<form\b[^>]*?\bmethod\s*=\s*(["\']?)post\1[^>]*>', re.I | re.S)


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


BACKUP_ROOT = 'phase7c_backups'


def backup(path):
    """Copy the original to phase7c_backups/<same path>  (outside app/, listed in .gitignore)."""
    target = os.path.join(BACKUP_ROOT, path)
    if not os.path.exists(target):                 # keep the FIRST original, even if the script runs twice
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(path, target)


def split_nl(raw):
    return ('\r\n' if '\r\n' in raw else '\n'), raw.replace('\r\n', '\n')


# ------------------------------------------------------------------ B) csrf tokens in every POST form
def add_tokens(text):
    """Returns (new_text, forms_found, forms_patched)."""
    out, pos, found, patched = [], 0, 0, 0
    for m in FORM_RE.finditer(text):
        found += 1
        out.append(text[pos:m.end()])
        pos = m.end()
        if 'csrf_token' in text[m.end():m.end() + 300]:
            continue
        line_start = text.rfind('\n', 0, m.start()) + 1
        indent = re.match(r'[ \t]*', text[line_start:m.start()]).group(0) if text[line_start:m.start()].strip() == '' else ''
        out.append('\n' + indent + '    ' + TOKEN_INPUT)
        patched += 1
    out.append(text[pos:])
    return ''.join(out), found, patched


def forms_without_token(text):
    return sum(1 for m in FORM_RE.finditer(text) if 'csrf_token' not in text[m.end():m.end() + 300])


def patch_logout(path='app/templates/base.html'):
    raw = read(path)
    nl, text = split_nl(raw)
    if "url_for('auth.logout')" not in text:
        print('!!', path, ': no logout link found (already changed?)')
        return
    if re.search(r'<form[^>]*auth\.logout', text):
        print('SKIP', path, ': logout is already a form')
        return
    pattern = re.compile(r"<a href=\"\{\{ url_for\('auth\.logout'\) \}\}\" class=\"([^\"]*)\">([^<]*)</a>")
    m = pattern.search(text)
    if not m:
        print('!!', path, ': logout link has an unexpected shape. Replace it by hand with:')
        print('   <form method="POST" action="{{ url_for(\'auth.logout\') }}" class="nav-logout-form">'
              + TOKEN_INPUT + '<button type="submit" class="btn btn-sm btn-secondary">Exit</button></form>')
        problems.append(path)
        return
    form = ('<form method="POST" action="{{ url_for(\'auth.logout\') }}" class="nav-logout-form">'
            + TOKEN_INPUT + '<button type="submit" class="' + m.group(1) + '">' + m.group(2) + '</button></form>')
    backup(path)
    write(path, text.replace(m.group(0), form, 1).replace('\n', nl))
    print('OK  ', path, ': logout is now a POST form')


def patch_all_templates(root='app/templates'):
    total_found = total_patched = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            raw = read(path)
            nl, text = split_nl(raw)
            new, found, patched = add_tokens(text)
            if found:
                print(f'     {path.replace(os.sep, "/")}: {found} POST form(s), {patched} newly tokenised')
            if patched:
                backup(path)
                write(path, new.replace('\n', nl))
            total_found += found
            total_patched += patched
    # verify EVERYTHING now has a token
    missing = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith('.html'):
                path = os.path.join(dirpath, name)
                if forms_without_token(split_nl(read(path))[1]):
                    missing.append(path)
    if missing:
        print('!! These templates still have a POST form without csrf token:', ', '.join(missing))
        print('   Send me exactly these files.')
        problems.extend(missing)
    else:
        print(f'OK   CSRF: {total_found} POST form(s) in templates, all carry a token')


def patch_css(path='app/static/css/chat.css'):
    if not os.path.isfile(path):
        print('!!', path, 'not found (Phase 6 css). Add this to any css file:  .nav-logout-form{display:inline;margin:0}')
        problems.append(path)
        return
    text = read(path)
    if 'nav-logout-form' in text:
        return
    write(path, text.rstrip() + '\n\n/* Phase 7: logout is a POST form */\n.nav-logout-form { display: inline; margin: 0; }\n')
    print('OK  ', path, ': .nav-logout-form added')


# ------------------------------------------------------------------ C) timezone
TZ_IMPORT = 'from app.timeutil import {names}\n'


def add_import(text, names):
    import ast
    line = TZ_IMPORT.format(names=names).rstrip('\n')
    if line in text:
        return text
    tree = ast.parse(text)
    last_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno <= 80:
            last_end = node.end_lineno             # end of the WHOLE statement, even if it spans lines
    lines = text.split('\n')
    lines.insert(last_end, line)
    return '\n'.join(lines)


TZ_FILES = {
    # path: (regex replacements, names to import)
    'app/models.py': ([(r'datetime\.now\(timezone\.utc\)\.date\(\)', 'app_today()'),
                       (r'\bdate\.today\(\)', 'app_today()')], 'app_today'),
    'app/main/routes.py': ([(r'\bdate\.today\(\)', 'app_today()'),
                            (r'\bdatetime\.now\(\)\.hour', 'app_now().hour')], 'app_today, app_now'),
    'app/smart/helpers.py': ([(r'datetime\.now\(timezone\.utc\)\.date\(\)', 'app_today()'),
                              (r'\bdate\.today\(\)', 'app_today()'),
                              (r'\btoday_utc\b', 'today_local')], 'app_today'),
    'app/smart/routes.py': ([(r'\bdate\.today\(\)', 'app_today()')], 'app_today'),
    'app/notifications/services.py': ([(r'\b_now\(\)\.date\(\)', 'app_today()'),
                                       (r'\bdate\.today\(\)', 'app_today()'),
                                       (r'letter\.created_at\.date\(\)', 'to_app_date(letter.created_at)'),
                                       (r'\btoday_utc\b', 'today_local')], 'app_today, to_app_date'),
}


def patch_timezone():
    if not os.path.isfile('app/timeutil.py'):
        print('!! app/timeutil.py missing (extract the zip first)')
        problems.append('app/timeutil.py')
        return
    for path, (edits, names) in TZ_FILES.items():
        if not os.path.isfile(path):
            print('--  ', path, ': not found, skipped')
            continue
        raw = read(path)
        nl, text = split_nl(raw)
        if 'app.timeutil' in text:
            print('SKIP', path, '(already uses timeutil)')
            continue
        new, total = text, 0
        for pattern, repl in edits:
            new, n = re.subn(pattern, repl, new)
            total += n
        if total == 0:
            print('--  ', path, ': nothing to change')
            continue
        new = add_import(new, names)
        try:
            compile(new, path, 'exec')
        except SyntaxError as e:
            print('!!', path, ': would not compile after edit, left unchanged:', e)
            problems.append(path)
            continue
        backup(path)
        write(path, new.replace('\n', nl))
        print(f'OK   {path}: {total} date/time spot(s) now use the app time zone')


if __name__ == '__main__':
    print('--- A) logout')
    patch_logout()
    patch_css()
    print('--- B) csrf tokens in forms')
    patch_all_templates()
    print('--- C) time zone')
    patch_timezone()
    print()
    if problems:
        print('Fix the "!!" items above first (send me ONLY those files).')
        sys.exit(1)
    print('Done. Restart:  python run.py   then run REGRESSION_CHECKLIST.md')
