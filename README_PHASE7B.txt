PHASE 7 PART 2 - lagane ke steps

1) git commit (ya folder copy).
2) Zip ko project root me extract karo (Replace: app/auth/routes.py, run.py; naya: app/ratelimit.py, apply_phase7b.py).
3) python apply_phase7b.py
   (main/routes.py, timeline.html, memory_form.html ko patch karta hai. "!!" dikhe to mujhe batao.)
4) App band karke dobara chalao:  python run.py
   - ab debug OFF hai: code badalne par server khud reload nahi hota, Ctrl+C karke dobara chalao.
   - phone par chalana ho (same Wi-Fi):   $env:HOST="0.0.0.0"; python run.py
5) PHASE7_FINAL_REPORT.md ki "Regression" list chalao.
6) Passwords badlo (abhi tak nahi kiya ho to).
