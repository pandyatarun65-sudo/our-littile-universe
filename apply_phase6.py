"""
Phase 6 setup script. Run ONCE from the project root (where run.py is):

    python apply_phase6.py

It edits 2 existing files for you (so you never paste code by hand):
  1. app/__init__.py          -> registers the chat + notifications blueprints
  2. app/templates/base.html  -> Chat link, bell icon, chat.css, notifications.js, csrf meta
It also CHECKS that app/models.py already has your Phase 6 models (ChatMessage, Notification,
User.last_seen). It does not change models.py.
A backup of each edited file is saved as <name>_backup_before_phase6.<ext>.
Running it twice is safe: parts that are already done are skipped.
"""
import re
import shutil
import sys

BELL = '''<a href="{{ url_for('notifications.notifications_page') }}" class="nav-bell" id="navBell" aria-label="Notifications">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
                        <span class="bell-badge" id="bellBadge" {% if not unread_notification_count %}hidden{% endif %}>{{ unread_notification_count or '' }}</span>
                    </a>
                    '''

todo = []


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def backup(path):
    dot = path.rfind('.')
    shutil.copy(path, path[:dot] + '_backup_before_phase6' + path[dot:])


def check_models(path='app/models.py'):
    text = read(path)
    needed = ['class ChatMessage', 'message_type', 'media_path', 'sent_at', 'is_deleted',
              'class Notification', 'recipient_id', 'link_endpoint', 'is_read', 'last_seen']
    missing = [n for n in needed if n not in text]
    if missing:
        print('!! app/models.py does not have your Phase 6 models yet (missing: %s).' % ', '.join(missing))
        print('   Put the Phase 6 models.py in place and run  python migrate_phase6.py  first.')
        sys.exit(1)
    print('OK   app/models.py: Phase 6 models found')


def patch_init(path='app/__init__.py'):
    text = read(path)
    if 'chat_bp' in text and 'notifications_bp' in text:
        print('SKIP app/__init__.py: already registered')
        return
    backup(path)
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    m = re.search(r'^([ \t]*)from app\.smart\.routes import smart_bp[ \t]*$', text, re.M)
    r = re.search(r'^([ \t]*)app\.register_blueprint\(smart_bp\)[ \t]*$', text, re.M)
    if not (m and r):
        print('!! app/__init__.py: could not find the smart_bp lines. Add these 4 lines inside create_app():')
        print('     from app.chat.routes import chat_bp')
        print('     from app.notifications.routes import notifications_bp')
        print('     app.register_blueprint(chat_bp)')
        print('     app.register_blueprint(notifications_bp)')
        todo.append('app/__init__.py')
        return
    text = text.replace(m.group(0), m.group(0) + '\n' + m.group(1) + 'from app.chat.routes import chat_bp\n' +
                        m.group(1) + 'from app.notifications.routes import notifications_bp', 1)
    r = re.search(r'^([ \t]*)app\.register_blueprint\(smart_bp\)[ \t]*$', text, re.M)
    text = text.replace(r.group(0), r.group(0) + '\n' + r.group(1) + 'app.register_blueprint(chat_bp)\n' +
                        r.group(1) + 'app.register_blueprint(notifications_bp)', 1)
    compile(text, path, 'exec')
    write(path, text.replace('\n', nl))
    print('OK   app/__init__.py: chat + notifications blueprints registered')


def patch_base(path='app/templates/base.html'):
    text = read(path)
    if 'nav-bell' in text:
        print('SKIP base.html: already patched')
        return
    backup(path)
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    problems = []

    a = "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">"
    if a in text:
        text = text.replace(a, a + "\n    <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/chat.css') }}\">"
                            "\n    {% if current_user.is_authenticated %}<meta name=\"csrf-token\" content=\"{{ csrf_token() }}\">{% endif %}", 1)
    else:
        problems.append('style.css <link>')

    dash = re.search(r"^([ \t]*)<a href=\"\{\{ url_for\('main\.dashboard'\) \}\}\" class=\"nav-item\">Dashboard</a>[ \t]*$", text, re.M)
    if dash:
        chat = (dash.group(1) + "<a href=\"{{ url_for('chat.index') }}\" class=\"nav-item\">Chat"
                "<span class=\"nav-dot\" id=\"chatDot\" {% if not chat_unread %}hidden{% endif %}></span></a>")
        text = text.replace(dash.group(0), dash.group(0) + '\n' + chat, 1)
    else:
        problems.append('Dashboard nav link')

    greet = '<span class="nav-user-greeting">'
    if greet in text:
        text = text.replace(greet, BELL + greet, 1)
    else:
        problems.append('nav-user-greeting')

    js = '{% block extra_js %}{% endblock %}'
    if js in text:
        text = text.replace(js, "{% if current_user.is_authenticated %}<script src=\"{{ url_for('static', filename='js/notifications.js') }}\" defer></script>{% endif %}\n    " + js, 1)
    else:
        problems.append('extra_js block')

    write(path, text.replace('\n', nl))
    if problems:
        print('!! base.html: could not place:', ', '.join(problems), '(see PHASE6_README.txt for the manual lines)')
        todo.append('base.html')
    else:
        print('OK   app/templates/base.html: Chat link, bell, chat.css, notifications.js added')


if __name__ == '__main__':
    check_models()
    patch_init()
    patch_base()
    print()
    print('Next: python migrate_phase6.py   (safe to run again), then python run.py' if not todo
          else 'Fix the "!!" items above first.')
