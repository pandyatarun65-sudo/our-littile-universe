# Our Little Universe — Phase 7: Security, Stability & Production-Readiness Audit

**Audit status: PARTIAL (v1).** Is report me sirf wahi files audit hui hain jo is chat me mujhe actually mili.
Jo files nahi mili unke baare me main kuch "secure" nahi keh sakta; wo neeche "NOT YET REVIEWED" me hain.
Koi application "100% secure" nahi hota. Ye report us claim ko nahi karti.

**Files jo maine padhi:** `config.py`, `app/__init__.py`, `app/models.py` (Phase 1–6), `app/utils.py`, `app/static/js/main.js`,
`app/templates/base.html`, `app/templates/dashboard.html`, `app/surprises/routes.py`, `app/main/routes.py` (Phase 2 + meri Phase 5 copy),
`app/smart/*` (Phase 5), `requirements.txt`, `migrate_phase6.py`, aur Phase 6 ka chat/notification code (`chat.js`, `notifications.js`, chat/notifications Python).

**NOT YET REVIEWED (zaroori):** `app/auth/routes.py` + `login.html` (login, password check, brute force, `next` redirect), `run.py` (debug mode),
`.gitignore` (existing), `.env` ke **sirf variable naam**, `fix_data_mismatch.py`, templates: `timeline.html`, `memory_form.html`, `gallery.html`,
`surprises/letter_view.html`, `letters_list.html`, `open_when_list.html`, `secret_box_list.html`, `letter_form.html`.

---
## 1. Findings (priority order)

Status: **VERIFIED** = code me dekha. **FIXED-HERE** = is package me fix hai. **NEED-FILE** = file chahiye.

### CRITICAL
Koi verified CRITICAL nahi mila. (H1 niche tab CRITICAL ban jata hai agar production me `SECRET_KEY` set na ho.)

### HIGH
| ID | Problem | Kahan | Status |
|---|---|---|---|
| H1 | **Kamzor default `SECRET_KEY`** (`'dev-key-change-me'`). Agar server pe env var na mile to app chalti rehti hai, aur GitHub public ho to koi bhi login cookie forge karke Tarun/Kuku ban sakta hai. | `config.py` | VERIFIED, FIXED-HERE |
| H2 | **Private memory photos bina login ke khulti hain.** Photos `app/static/uploads/` me hain; Flask static files login check nahi karta. Sirf 128-bit random naam bachata hai (URL history, screenshot, referrer se leak ho sakta hai). | `utils.py`, templates (`url_for('static', …)`) | VERIFIED, FIXED-HERE |
| H3 | **Password plaintext me share hua.** Blueprint text me ek account ka password likha tha aur wo chat me paste hua. | chat/blueprint (code me nahi) | VERIFIED → **tumhe password badalna hai** |

### MEDIUM
| ID | Problem | Kahan | Status |
|---|---|---|---|
| M1 | **Purane forms me CSRF token nahi** (memory add/edit/delete, letters create/edit/delete). Routes token check nahi karte. | `main/routes.py`, `surprises/routes.py` | VERIFIED, FIXED-HERE (same-origin check + SameSite=Lax) |
| M2 | **Photo upload sirf extension se check hota tha**, content se nahi (`shell.jpg` me kuch bhi ho sakta tha). | `utils.py` | VERIFIED, FIXED-HERE |
| M3 | **Memory edit/delete me ownership check nahi.** Koi bhi logged-in user kisi ki bhi memory badal/hata sakta hai. Do-user shared journal me ye design choice ho sakta hai, lekin ye tumhare "authorization" rule se match nahi karta. | `main/routes.py` | VERIFIED, **tumhara decision** (neeche) |
| M4 | **Security headers nahi**, custom error pages nahi. | `__init__.py` | VERIFIED, FIXED-HERE |
| M5 | **Purani dependency versions.** `Werkzeug 3.0.3` me known advisories hain (`safe_join` Windows device names: CVE-2025-66221 → fix 3.1.4, CVE-2026-21860 → 3.1.5, CVE-2026-27199 → 3.1.6). Flask 3.1.3 ek security-fix release hai. Zyada asar Windows pe (tumhara laptop); Linux/Render pe kam. | `requirements.txt` | VERIFIED, `requirements.new.txt` diya (nahi apply kiya) |
| M6 | **SQLite foreign keys ON nahi** (SQLite default me enforce nahi karta) → orphan records ban sakte hain. `busy_timeout` bhi nahi → chat polling + writes me "database is locked" ka chance. | models / engine | VERIFIED, FIXED-HERE |
| M7 | **Letter edit/delete routes tootay hue** (`<int:letter_id>` copy karte waqt kat gaya). Edit/delete kaam nahi karte. | `surprises/routes.py` | VERIFIED, FIXED in `phase6.zip` ki `surprises/routes.py` (wo zip lagana zaroori) |
| M8 | **Unlock UTC date se hota hai.** India me "10 Oct" ka letter 10 Oct ko **subah 05:30** khulta hai, midnight ko nahi. Phase 5 (daily question, special dates) local date use karte hain, to inconsistency bhi hai. | `models.py: is_unlocked` | VERIFIED, optional (Phase 4 logic chhedna nahi tha) |
| M9 | **Login pe brute-force protection / rate limit** ka pata nahi. | `auth/routes.py` | NEED-FILE |
| M10 | **Locked letter ka body page me chhipa to nahi?** Route sahi hai (recipient ko locked=True), lekin template `letter_view.html` me `letter.body` locked state me print hota hai ya nahi, dekhna padega. | `letter_view.html` | NEED-FILE |

### LOW / INFO
- LOW: letters edit/delete non-author ko **403** (existence batata hai), view **404** deta hai. Chhota inconsistency.
- LOW: titles/body ki server-side length limit nahi (sirf 5 MB request limit).
- LOW: `User.query.get()` legacy style (SQLAlchemy 2 me deprecated, chal raha hai).
- LOW: `GET /notifications/<id>/go` read mark karta hai (GET se state change) — sirf apni notification, nuksan nahi.
- LOW (perf): timeline/gallery sab memories ek saath load karte hain; template me `memory.photos` N+1 query ho sakti hai (template dekha nahi).
- INFO: Typing indicator server memory me hai → production me **gunicorn `--workers 1`** rakho.
- INFO: Google Fonts third-party se load hota hai (privacy); `onclick` inline (strict CSP lagane me dikkat) — CSP abhi nahi lagayi.
- INFO (good): Jinja autoescape ON, `nl2br` filter pehle escape karta hai, kahin `|safe`/`Markup` template me nahi mila (jo dekhe). `main.js` me `innerHTML/eval/fetch/localStorage` nahi. `chat.js` sirf `textContent`.

---
## 2. Two-user privacy audit (jo files dekhi unke hisaab se)
| Resource | Result |
|---|---|
| Chat messages | OK — har query "sender YA recipient = main"; delete sirf sender; baaki ko 404 |
| Chat voice / images | OK — static ke bahar, `/chat/media/<id>` participant check, server-generated naam + regex re-check |
| Notifications | OK — sirf `recipient_id == me`; baaki 404; link whitelist; letter link tabhi jab user us letter ka sender/recipient ho |
| Letters / Open When / Secret Box | Route level OK (sirf author/recipient; edit/delete author). Body leak locked template pe depend (**M10**) |
| Daily answers | OK — save hamesha `current_user.id`; partner ka text tabhi jab main khud answer de chuka hoon; history sirf mere answered din |
| Special dates | OK — dono dekh sakte hain, edit/delete sirf creator |
| Memories / Photos | **By design shared** (dono dekhte hain). Edit/delete unrestricted (**M3**). Photo files ab login ke peeche (**H2 fixed**) |

IDOR test: `/surprises/<id>`, `/chat/media/<id>`, `/chat/<id>/delete`, `/notifications/<id>/go` — sab me ID badalne par doosre ka resource nahi milta (code padhke + Phase 6 ke tests se).

## 3–4. Media + real-time
- Chat me WebSocket nahi hai, **polling** hai (`/chat/poll`, `/chat/typing`, `/chat/seen`) — sab `@login_required`, server khud user chunta hai (client se user-id kabhi nahi aata).
- Upload: ab content-bytes se type check (jpg/png/gif/webp), extension sirf secondary; naam server banata hai; delete sirf `uploads/` ke andar; chat media size ≤ 5 MB, path regex-validated.
- Memory photos ke liye ab login zaroori (H2). Chat media pehle se authenticated route se.

## 5. Database
Models padhe. Dikkatein: FK enforcement off (M6, fixed), `chat_messages` pe composite index nahi (abhi chhota data, zaroorat nahi), `Notification` pe dedupe column nahi (code se handle), timestamps mixed UTC/local (M8). Legacy `user/memory/photo` tables kahin query nahi hote (grep: nahi mile). Kuch bhi delete/recreate nahi kiya.

## 6–7. Config + dependencies
- `SECRET_KEY` env se; production me weak/missing → app start hi nahi hoti (H1 fix). Debug `False` config me; `run.py` **dekhna baaki** (`debug=True` nahi hona chahiye).
- `requirements.txt`: Flask (framework), Flask-SQLAlchemy (DB), Flask-Login (login sessions), python-dotenv (.env), Werkzeug (Flask ka core) — **sab use ho rahe hain, koi extra nahi**. `gunicorn` missing (server ke liye chahiye). Naye pinned versions `requirements.new.txt` me. **Pehle laptop pe install karke poori checklist chalao**; kuch toote to purani file wapas rakh do.

## 8–10. Errors, performance, mobile
- Errors: 400/401/403/404/413/500 ke friendly pages (chat/notifications ke liye JSON), stack trace user ko nahi. DB error pe `session.rollback()`.
- Performance: chat paginated (30), notifications poll 30s, dashboard queries chhoti; timeline N+1 shaq (template chahiye).
- Mobile: Phase 6 me `visualViewport` se keyboard-safe height, 16px input (iOS zoom nahi), touch targets 40px. Long text `overflow-wrap:anywhere`. Orientation change `resize` listener se.

## 11. Git / GitHub safety
`.gitignore` (is package me) `.env`, `instance/`, `*.db`, `app/static/uploads/*`, `backups/`, `*.zip`, `venv/` sab block karta hai. `.env.example` (sirf naam) diya.
**Zaroori check (history):** agar kabhi pehle `.env` / database / photos commit hui thi, to wo history me rehti hain. Chalao:
```
git log --all --oneline -- .env instance app/static/uploads
git ls-files | findstr /i "\.env database.db uploads"
```
Kuch dikhe to mujhe batao (history saaf karni padegi) — **aur us case me SECRET_KEY aur passwords badal do.** Repo **Private** rakho.

## 12. Backup & recovery
`python backup_olu.py` → `backups/olu_backup_<time>.zip` (DB ka consistent snapshot + memory photos + chat media; aakhri 10 rakhta hai). `.env` backup me nahi — password manager me rakho.
Kya backup hona chahiye: `instance/database.db`, `app/static/uploads/`, `instance/chat_media/`, `.env` (alag, secure jagah).
Restore: app band karo → `database.db` ko `instance/` me, `uploads/` ko `app/static/uploads/`, `chat_media/` ko `instance/chat_media/` me rakho → app chalao.
Rule: **hafte me ek baar** + bada change karne se pehle; backup zip ko **GitHub pe kabhi nahi**, apne drive/pen-drive me (ya encrypted).

## 13. Production readiness (Render free)
| Cheez | Status |
|---|---|
| HTTPS | Render deta hai ✔ (mic ke liye zaroori) |
| Secure cookies / SECRET_KEY / debug | config se ready; Render env me `APP_ENV=production`, `SECRET_KEY=<64 hex>` set karo |
| Gunicorn | `gunicorn "app:create_app()" --workers 1 --threads 4` (requirements me gunicorn) |
| **Data persistence** | **NOT READY** — free plan ka disk ephemeral: database, uploads, chat_media restart/redeploy pe mit sakte hain |
| Fresh DB pe 2 users | Naye server pe DB khaali hogi: Tarun/Kuku ke accounts banane ki script `.env` se chahiye (`fix_data_mismatch.py` dekhna baaki) |
| Logging | Flask default; passwords log nahi hote (auth file dekhni baaki) |
| WebSocket | Lagu nahi (polling) ✔ |
Deploy **maine nahi kiya**, na karunga jab tak tum na kaho.

## 14. Fix list
**CRITICAL:** — (koi nahi)
**HIGH (is package me):** H1 `config.py`; H2 `hardening.py` (photos login ke peeche); H3 *tumhara kaam: password badlo*.
**MEDIUM (is package me):** M1 same-origin check + SameSite; M2 `utils.py`; M4 headers + errors; M6 SQLite pragmas; M7 `phase6.zip` ki surprises routes.
**MEDIUM (tumhara decision / file chahiye):** M3 ownership, M5 dependency upgrade, M8 timezone, M9 brute-force, M10 letter template.
**OPTIONAL:** CSP, `Query.get` → `db.session.get`, timeline pagination, chat index.

**M3 ka decision:** (A) abhi jaisa — dono ek doosre ki memories edit/delete kar sakte hain, ya (B) sirf jisne banayi wo. Batao, B ka 6-line patch main de dunga.

## 15. Regression — maine kya chalaya, tumhe kya chalana hai
Maine chalaya (sandbox, real Flask, DB stubbed): private-photo gate (401/200/404), same-origin check (same/other/`null` origin, referer), headers, error pages (JSON vs HTML, no trace), upload content check (fake `.jpg` PHP/HTML reject), delete confinement (`../` fail), `apply_phase7` do baar, backup zip + restore.
**Tumhe chalana hai (laptop pe, dono users ke saath):**
- AUTH: login/logout; logout ke baad `/chat`, `/timeline` login par bhejte hain
- MEMORIES: add (photo ke saath), edit, delete, timeline, search; **timeline/gallery/dashboard me photos dikhti hain** (login ke baad); incognito window me kisi photo ka URL kholo → 401
- LETTERS/OPEN WHEN/SECRET BOX: create, locked view, unlock, **edit/delete** (phase6.zip ke baad), recipient authorization
- PHASE 5: On This Day, Daily Question, Special Dates, search filters
- PHASE 6: chat send/receive, ticks, notifications, voice (localhost), photo, reply, typing, online/last seen
- Naya: kisi bhi form ko normal tarah save karo (CSRF check se kuch nahi tootna chahiye); `/random-url` → friendly 404 page; ek bada (>5 MB) photo → "file too large" message

## 16. Final report
| Item | Status |
|---|---|
| Overall security rating | **NEEDS WORK** (partial audit; fixes ke baad bhi login/auth aur kuch templates dekhne baaki) |
| Critical | 0 verified |
| High | 3 (2 code fixed here, 1 tumhara password change) |
| Medium | 10 (5 fixed here, 1 phase6.zip me, 4 tumhare decision/file par) |
| Low / Info | 14 |
| Remaining risks | auth routes + 8 templates unreviewed; memory ownership; dependency upgrade untested; ephemeral hosting |
| Production readiness | **NOT READY** (persistence + auth review baaki) |
| GitHub readiness | **NEEDS WORK** → `.gitignore` lagao + history check chalao |
| Deployment readiness | **NOT READY** (free-plan data loss, user seeding, gunicorn pin) |
| Backup readiness | **READY** (script test hui; schedule tumhe rakhna hai) |
