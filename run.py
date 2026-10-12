import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Safe defaults: debug OFF and only this computer can connect.
    #   Phone on the same Wi-Fi (PowerShell):  $env:HOST="0.0.0.0"; python run.py
    #   Debug + auto-reload (only when YOU need it, never on a server):  $env:FLASK_DEBUG="1"; python run.py
    # (The Werkzeug debugger lets anyone who can reach the port run code - never combine debug with HOST=0.0.0.0.)
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=debug)
