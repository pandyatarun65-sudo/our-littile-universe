from app import create_app

app = create_app()

if __name__ == '__main__':
    # debug=True gives you auto-reload and detailed error pages while
    # developing. Turn this off (debug=False) before any real deployment.
    app.run(host='0.0.0.0', port=5000, debug=True)