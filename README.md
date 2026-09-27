# Our Little Universe

A private digital memory & relationship app for two people — a shared timeline,
photo gallery, and letters, built as a personal learning project.

**Status:** Phase 1 (Foundation) — login, dashboard, and timeline with sample data.

## Technologies

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite
- **Frontend:** HTML (Jinja2 templates), CSS, vanilla JavaScript
- **Tools:** VS Code, Git, GitHub

## Project Structure

```
our-little-universe/
├── app/
│   ├── __init__.py        # App factory
│   ├── models.py           # Database models
│   ├── auth/routes.py      # Login/logout
│   ├── main/routes.py      # Dashboard/timeline
│   ├── static/css, js
│   └── templates/
├── instance/                # SQLite database file (not in Git)
├── config.py
├── init_db.py               # Creates tables + sample data
├── requirements.txt
├── run.py
├── .env.example
└── .gitignore
```

## Installation

### 1. Create a virtual environment

A virtual environment keeps this project's Python packages separate from
the rest of your computer.

**Windows:**
```
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```
python3 -m venv venv
source venv/bin/activate
```

You'll know it worked because your terminal prompt now starts with `(venv)`.

### 2. Install dependencies

```
pip install -r requirements.txt
```

This reads `requirements.txt` and installs Flask and the other packages
listed there.

### 3. Set up your environment variables

```
cp .env.example .env
```

(On Windows, just copy the file manually or use `copy .env.example .env`.)

Open `.env` and set your own `SECRET_KEY` and the two users' names, emails,
and passwords. These are the real login credentials for the app.

### 4. Initialize the database

```
python init_db.py
```

This creates `instance/database.db`, makes your two user accounts, and adds
a few sample memories so the timeline isn't empty.

### 5. Run the app

```
python run.py
```

You should see output including a line like `Running on http://127.0.0.1:5000`.

### 6. Open the website

Go to **http://127.0.0.1:5000** in your browser. Log in with one of the
emails/passwords you set in `.env`.

## Basic Git Commands

```
git init                  # Start tracking this folder with Git
git status                # See what's changed
git add .                 # Stage all changed files
git commit -m "message"   # Save a snapshot with a description
git log                   # See your commit history
```

## Creating the GitHub Repository

1. Go to https://github.com and click **New repository**.
2. Name it `our-little-universe`, keep it **Private**, don't add a README
   (you already have one).
3. Click **Create repository** — GitHub will show you commands like these:

```
git remote add origin https://github.com/YOUR_USERNAME/our-little-universe.git
git branch -M main
git push -u origin main
```

Run those from inside your project folder (after `git init`, `git add .`,
and your first `git commit`).

## Notes

- `.env` and `instance/` are in `.gitignore` on purpose — they contain your
  real passwords and personal data. Never remove them from `.gitignore`.
- This is Phase 1 only. Adding memories, photos, and letters through the UI
  comes in later phases.
