PHASE 7 - kya lagana hai (5 minute)

1) git commit karo (ya folder ki copy).
2) Is zip ko project root me extract karo (replace: config.py, app/utils.py, .gitignore, baaki naye).
   - agar tumhare paas pehle se .gitignore hai to usme se apni extra lines mila lena.
   - requirements.new.txt ko ABHI mat rakho (pehle neeche step 6).
3) python apply_phase7.py           (app/__init__.py me init_security(app) jodta hai)
4) .env me SECRET_KEY hona chahiye (32+ random characters). Naya banane ke liye:
      python -c "import secrets; print(secrets.token_hex(32))"
   (Isse sab logged-in sessions logout ho jayenge - normal hai.)
5) python run.py  -> report ki "15. Regression" checklist chalao.
6) Dependencies (optional, baad me):  copy requirements.txt requirements.old.txt
      copy requirements.new.txt requirements.txt
      pip install -r requirements.txt     -> phir checklist dobara. Kuch toote to old wapas.
7) Backup:  python backup_olu.py
8) Dono accounts ke passwords badlo (blueprint wala password chat me share hua tha); .env me hi rakho.

Server (Render) env vars:  APP_ENV=production, SECRET_KEY=<64 hex>, SESSION_COOKIE ke liye kuch aur nahi.
