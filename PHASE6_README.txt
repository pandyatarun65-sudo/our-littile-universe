OUR LITTLE UNIVERSE - PHASE 6 (chat, notifications, voice, photos, typing, online status)
==========================================================================================
Ye package TUMHARI models.py ke hisaab se bana hai (ChatMessage, Notification, User.last_seen).

STEP 0  Backup:   git commit karo, ya project folder ki copy rakh lo.

STEP 1  Zip ko project ke root me (jahan run.py hai) extract karo. "Replace files" aaye to Yes.
        Replace hone wali files:  app/surprises/routes.py  (URL bug fix + notifications)
                                  app/smart/routes.py      (csrf helper + notification)
        Nayi files:  app/security.py, app/chat/*, app/notifications/*,
                     app/templates/chat.html, notifications.html,
                     app/static/css/chat.css, app/static/js/chat.js, notifications.js,
                     apply_phase6.py

STEP 2  Database (agar pehle nahi chalaya):   python migrate_phase6.py      (dobara chalana safe hai)

STEP 3  Setup script:                         python apply_phase6.py
        (app/__init__.py me 2 blueprints register karti hai, base.html me Chat link + bell lagati hai.
         "!!" dikhe to wahi line haath se karo.)

STEP 4  Chalao:  python run.py      -> Tarun aur Kuku dono ko alag browsers me login karke test karo.

MIC (voice) sirf  http://127.0.0.1:5000  ya  https  par chalta hai. Phone par http://192.168.x.x:5000
se mic block hoga. Phone par voice test = Render (https) par.

RENDER (free): gunicorn me sirf ONE worker rakho (typing indicator server ki memory me rehta hai):
    gunicorn "app:create_app()" --workers 1 --threads 4
Free plan par database + chat_media + uploads reset ho sakte hain (ephemeral disk).

-------------------------------------------------------------------------------
TESTING CHECKLIST  (Tarun = browser 1, Kuku = browser 2 / incognito)
-------------------------------------------------------------------------------
AUTH      [ ] logout karke /chat kholo -> login page aata hai
          [ ] /chat/messages aur /chat/media/1 bina login -> login par redirect
CHAT      [ ] Tarun message bhejta hai -> Kuku ko ~3 sec me dikhta hai
          [ ] Kuku Reply dabake jawab deta hai -> upar chhota quoted box; us par click -> original par scroll
          [ ] Kal/aaj ke messages ke beech date separator ("Today", "Yesterday")
          [ ] 30 se zyada messages -> "Load earlier messages"
          [ ] Search (magnifier) -> result par click -> message highlight hota hai
          [ ] Apne message par Delete -> dono taraf "This message was deleted"
          [ ] Kuku ke message par Delete button hi nahi dikhta
STATUS    [ ] Tarun ke message par pehle ✓ (sent), Kuku ka app khulte hi ✓✓ (delivered), chat dekhte hi ✓✓ sunehri (seen)
NOTIF     [ ] Kuku jab chat par nahi hai: bell par badge 1, "New message from Tarun"
          [ ] Notification par click -> chat khulti hai aur wo read ho jati hai
          [ ] "Mark read" aur "Mark all as read" kaam karte hain
          [ ] Naya letter / Open When / Secret Box bhejo -> doosre ko notification
          [ ] Kuku daily question ka answer de -> Tarun ko notification
          [ ] Aisa letter jiski unlock date aaj ki ho (kal tak future thi) -> "has unlocked"
PHOTO     [ ] Photo icon -> preview -> Send -> chat me dikhti hai, click par bada viewer
          [ ] .txt / .exe ko .jpg naam dekar bhejo -> "That file type is not supported."
          [ ] /chat/media/<id> ko teesre (logged-out) browser me kholo -> login par chala jata hai
VOICE     [ ] Mic -> permission -> Stop -> preview (sunke dekho) -> Send
          [ ] Voice par play/pause, duration (0:07) dikhta hai
          [ ] Delete karne ke baad /chat/media/<id> -> 404
TYPING    [ ] Kuku type kare -> Tarun ko "Kuku is typing..." ~5 sec baad apne aap hat jata hai
          [ ] Database me typing ke liye koi row nahi banti
PRESENCE  [ ] Dusra browser band karo -> ~1-2 min me "Last seen recently", phir "Last seen today at ..."
MOBILE    [ ] Phone par keyboard khulne par input bar dikhta rehta hai
          [ ] Lambi image/screen fit hoti hai; nav toggle (☰) ab bhi chalta hai
REGRESSION[ ] Dashboard, Timeline, Gallery, Search, Letters (kholna + edit + delete), Open When, Secret Box,
              Special Dates, Daily Question sab pehle jaise

-------------------------------------------------------------------------------
SECURITY CHECKLIST
-------------------------------------------------------------------------------
[x] Har route par @login_required; doosra user server khud chunta hai (browser se recipient nahi aata)
[x] Har message query "main sender YA recipient hoon" tak limited (ID badalne se doosre ka message nahi milta)
[x] Delete sirf sender; anya ke liye 404 (existence leak nahi)
[x] Media static folder ke bahar (instance/chat_media), sirf /chat/media/<id> se, participant check ke baad
[x] File type: file ke andar ke bytes se check (extension/browser MIME par bharosa nahi), size limit 5 MB
[x] Stored naam server banata hai (32 hex + fixed extension) -> path traversal nahi; serve karte waqt dobara regex check
[x] Response me nosniff + private cache header
[x] Chat/notification text page par textContent se (innerHTML nahi) -> XSS nahi; Jinja autoescape
[x] Saare POST par CSRF token (header ya form)
[x] Notification link: sirf whitelist wale endpoints; letter link tabhi jab user us letter ka sender/recipient ho
[x] Notification sirf apni (recipient_id == current_user.id), doosre ki -> 404
[x] Presence: last-seen timestamp tabhi jab fully offline; koi history table nahi
[x] Typing: sirf memory, database me nahi
[ ] BAAKI (tumhare upar): .env / SECRET_KEY production me strong rakho; purane forms (memory add/delete, letters)
    me abhi CSRF token nahi hai
