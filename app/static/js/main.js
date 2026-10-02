document.addEventListener('DOMContentLoaded', () => {
    const fadeItems = document.querySelectorAll('.timeline-row, .gallery-item, .stat-card');
    fadeItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 70}ms`;
    });

    const navToggle = document.getElementById('navToggle');
    const mainNav = document.getElementById('mainNav');
    if (navToggle && mainNav) {
        navToggle.addEventListener('click', () => {
            const isOpen = mainNav.classList.toggle('is-open');
            navToggle.classList.toggle('is-active', isOpen);
            navToggle.setAttribute('aria-expanded', isOpen);
        });
    }

    const photoInput = document.getElementById('photo');
    const uploadPreview = document.getElementById('uploadPreview');
    const placeholderText = document.getElementById('uploadPlaceholderText');
    if (photoInput && uploadPreview) {
        photoInput.addEventListener('change', () => {
            const file = photoInput.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                uploadPreview.style.backgroundImage = `url(${event.target.result})`;
                if (placeholderText) placeholderText.hidden = true;
            };
            reader.readAsDataURL(file);
        });
    }

    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    const lightboxImage = document.getElementById('lightbox-image');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const closeButton = document.getElementById('lightbox-close');

    function openLightbox(src, caption) {
        lightboxImage.src = src;
        lightboxCaption.textContent = caption || '';
        lightbox.hidden = false;
    }

    function closeLightbox() {
        lightbox.hidden = true;
        lightboxImage.src = '';
    }

    document.querySelectorAll('.gallery-item').forEach((item) => {
        item.addEventListener('click', () => {
            openLightbox(item.dataset.src, item.dataset.caption);
        });
    });

    closeButton.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', (event) => {
        if (event.target === lightbox) closeLightbox();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeLightbox();
    });
});
/*
 * Phase 6 chat (vanilla JS).
 * How it stays "live": every ~3 seconds we ask the server /chat/poll
 * (new messages + ticks + typing + online). No WebSocket needed for two people.
 * Everything from the server is put on the page with textContent (never innerHTML) -> no XSS.
 */
(function () {
    'use strict';

    var app = document.getElementById('chatApp');
    if (!app) return;

    var ME = Number(app.dataset.me);
    var PARTNER = app.dataset.partner;
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var CSRF = csrfMeta ? csrfMeta.content : '';

    function $(id) { return document.getElementById(id); }
    var el = {
        scroll: $('chatScroll'), list: $('chatList'), older: $('loadOlder'), typing: $('typingLine'),
        presence: $('presenceLine'), form: $('chatForm'), input: $('chatInput'), send: $('sendBtn'),
        attach: $('attachBtn'), imageInput: $('imageInput'), mic: $('micBtn'),
        replyBar: $('replyBar'), replyWho: $('replyWho'), replyPreview: $('replyPreview'), replyCancel: $('replyCancel'),
        pending: $('pendingBar'), error: $('chatError'),
        searchBtn: $('chatSearchBtn'), search: $('chatSearch'), searchInput: $('chatSearchInput'), searchResults: $('chatSearchResults')
    };

    // ---------------------------------------------------------------- state
    var messages = new Map();      // id -> message object from the server
    var oldestId = null;
    var pollCursor = 0;            // highest id we have fetched (used by /chat/poll)
    var hasMore = false;
    var loadingOlder = false;
    var lastDayKey = null;
    var replyTo = null;
    var pending = null;            // {kind, blob, url, durationMs, ext} waiting to be sent
    var rec = null;                // active recording
    var recTimer = null;
    var currentAudio = null;
    var pollTimer = null;
    var lastSeenSent = 0;
    var lastTypingPing = 0;

    // ---------------------------------------------------------------- helpers
    function div(cls) { var d = document.createElement('div'); if (cls) d.className = cls; return d; }
    function btn(cls, text, label) {
        var b = document.createElement('button');
        b.type = 'button'; b.className = cls; b.textContent = text;
        if (label) b.setAttribute('aria-label', label);
        return b;
    }

    function api(path, opts) {
        opts = opts || {};
        var headers = Object.assign({ 'X-CSRF-Token': CSRF }, opts.headers || {});
        return fetch(path, Object.assign({ credentials: 'same-origin' }, opts, { headers: headers }))
            .then(function (res) {
                if (res.status === 204) return {};
                if (res.status === 413) throw new Error('That file is too large.');
                var type = res.headers.get('content-type') || '';
                if (res.redirected || type.indexOf('application/json') === -1) {
                    location.reload();                       // session ended -> login page
                    throw new Error('Please log in again.');
                }
                return res.json().then(function (data) {
                    if (!res.ok) throw new Error(data.error || 'Something went wrong.');
                    return data;
                });
            });
    }

    var errorTimer = null;
    function showError(text) {
        el.error.textContent = text;
        el.error.hidden = false;
        clearTimeout(errorTimer);
        errorTimer = setTimeout(function () { el.error.hidden = true; }, 5000);
    }

    var timeFmt = new Intl.DateTimeFormat([], { hour: 'numeric', minute: '2-digit' });
    function dayKey(d) { return d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate(); }
    function dayLabel(d) {
        var now = new Date();
        if (dayKey(d) === dayKey(now)) return 'Today';
        if (dayKey(d) === dayKey(new Date(now.getTime() - 86400000))) return 'Yesterday';
        return d.toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    }
    function fmtDur(ms) {
        var s = Math.round((ms || 0) / 1000);
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }
    function isNearBottom() { return el.scroll.scrollHeight - el.scroll.scrollTop - el.scroll.clientHeight < 140; }
    function scrollBottom() { el.scroll.scrollTop = el.scroll.scrollHeight; }
    function nodeFor(id) { return el.list.querySelector('[data-id="' + Number(id) + '"]'); }

    // ---------------------------------------------------------------- building message nodes
    var TICKS = { sent: '\u2713', delivered: '\u2713\u2713', seen: '\u2713\u2713' };
    var TICK_TEXT = { sent: 'Sent', delivered: 'Delivered', seen: 'Seen' };

    function buildReply(r) {
        var b = btn('msg-reply', '', 'Go to the original message');
        if (r.deleted) {
            b.classList.add('is-gone');
            b.textContent = 'Original message was deleted';
            b.disabled = true;
            return b;
        }
        var who = document.createElement('b');
        who.textContent = r.mine ? 'You' : PARTNER;
        var text = document.createElement('span');
        text.textContent = r.preview;
        b.appendChild(who); b.appendChild(text);
        b.addEventListener('click', function (e) { e.stopPropagation(); jumpTo(r.id); });
        return b;
    }

    function buildImage(m) {
        var img = document.createElement('img');
        img.className = 'msg-image'; img.alt = 'Photo'; img.loading = 'lazy'; img.src = m.media_url;
        img.addEventListener('load', function () { if (isNearBottom()) scrollBottom(); });
        img.addEventListener('click', function (e) { e.stopPropagation(); openViewer(m.media_url); });
        return img;
    }

    function buildVoice(m) {
        var wrap = div('voice');
        var play = btn('voice-btn', '\u25B6', 'Play voice message');
        var bar = div('voice-bar'); var fill = div('voice-fill'); bar.appendChild(fill);
        var time = document.createElement('span'); time.className = 'voice-time'; time.textContent = fmtDur(m.duration_ms);
        var audio = null;
        var total = m.duration_ms || 0;

        function reset() { play.textContent = '\u25B6'; fill.style.width = '0'; time.textContent = fmtDur(total); }
        play.addEventListener('click', function (e) {
            e.stopPropagation();
            if (!audio) {
                audio = new Audio(m.media_url);
                audio.preload = 'auto';
                audio.addEventListener('play', function () { play.textContent = '\u275A\u275A'; });
                audio.addEventListener('pause', function () { if (!audio.ended) play.textContent = '\u25B6'; });
                audio.addEventListener('ended', reset);
                audio.addEventListener('timeupdate', function () {
                    var len = total || (isFinite(audio.duration) ? audio.duration * 1000 : 0);
                    if (len) fill.style.width = Math.min(100, (audio.currentTime * 1000 / len) * 100) + '%';
                    time.textContent = fmtDur(audio.currentTime * 1000);
                });
                audio.addEventListener('error', function () { showError('Could not play that voice message.'); reset(); });
            }
            if (currentAudio && currentAudio !== audio) currentAudio.pause();
            if (audio.paused) { currentAudio = audio; audio.play().catch(function () {}); } else { audio.pause(); }
        });
        wrap.appendChild(play); wrap.appendChild(bar); wrap.appendChild(time);
        return wrap;
    }

    function buildMessage(m) {
        var row = div('msg ' + (m.mine ? 'msg-mine' : 'msg-theirs') + (m.deleted ? ' msg-deleted' : ''));
        row.dataset.id = m.id;
        var bubble = div('msg-bubble');

        if (m.reply && !m.deleted) bubble.appendChild(buildReply(m.reply));

        if (m.deleted) {
            bubble.textContent = 'This message was deleted';
        } else if (m.kind === 'image' && m.media_url) {
            bubble.appendChild(buildImage(m));
        } else if (m.kind === 'voice' && m.media_url) {
            bubble.appendChild(buildVoice(m));
        } else {
            var text = div('msg-text'); text.textContent = m.body || ''; bubble.appendChild(text);
        }

        var meta = div('msg-meta');
        var t = document.createElement('span');
        t.textContent = timeFmt.format(new Date(m.created_at));
        meta.appendChild(t);
        if (m.mine && !m.deleted && m.status) {
            var tick = document.createElement('span');
            tick.className = 'msg-status' + (m.status === 'seen' ? ' is-seen' : '');
            tick.textContent = TICKS[m.status];
            tick.title = TICK_TEXT[m.status];
            tick.setAttribute('aria-label', TICK_TEXT[m.status]);
            meta.appendChild(tick);
        }
        if (!m.deleted) bubble.appendChild(meta);
        row.appendChild(bubble);

        if (!m.deleted) {
            var actions = div('msg-actions');
            var reply = btn('', 'Reply');
            reply.addEventListener('click', function (e) { e.stopPropagation(); setReply(m); });
            actions.appendChild(reply);
            if (m.mine) {
                var del = btn('', 'Delete');
                del.addEventListener('click', function (e) { e.stopPropagation(); deleteMessage(m); });
                actions.appendChild(del);
            }
            row.appendChild(actions);
            row.addEventListener('click', function () { row.classList.toggle('msg-open'); });   // phones: tap to show actions
        }
        return row;
    }

    function buildSeparator(d) {
        var sep = div('chat-sep'); var s = document.createElement('span'); s.textContent = dayLabel(d);
        sep.appendChild(s); return sep;
    }

    function remember(m) {
        messages.set(m.id, m);
        oldestId = oldestId === null ? m.id : Math.min(oldestId, m.id);
    }
    function appendNode(m) {
        var d = new Date(m.created_at);
        if (dayKey(d) !== lastDayKey) { el.list.appendChild(buildSeparator(d)); lastDayKey = dayKey(d); }
        el.list.appendChild(buildMessage(m));
    }
    function renderAll() {
        if (currentAudio) currentAudio.pause();
        el.list.replaceChildren();
        lastDayKey = null;
        Array.from(messages.values()).sort(function (a, b) { return a.id - b.id; }).forEach(appendNode);
    }
    function replaceNode(m) {
        var old = nodeFor(m.id);
        if (old) old.replaceWith(buildMessage(m));
    }

    // ---------------------------------------------------------------- loading
    function loadInitial() {
        return api('/chat/messages').then(function (data) {
            data.messages.forEach(function (m) { remember(m); pollCursor = Math.max(pollCursor, m.id); });
            hasMore = data.has_more;
            el.older.hidden = !hasMore;
            renderAll(); scrollBottom(); markSeen();
        }).catch(function (e) { showError(e.message); });
    }

    function loadOlder() {
        if (!hasMore || loadingOlder || oldestId === null) return Promise.resolve();
        loadingOlder = true;
        var before = el.scroll.scrollHeight;
        return api('/chat/messages?before_id=' + oldestId).then(function (data) {
            data.messages.forEach(remember);
            hasMore = data.has_more;
            el.older.hidden = !hasMore;
            renderAll();
            el.scroll.scrollTop = el.scroll.scrollHeight - before;
        }).catch(function (e) { showError(e.message); }).then(function () { loadingOlder = false; });
    }

    function jumpTo(id) {
        var tries = 0;
        function step() {
            if (!messages.has(id) && hasMore && tries < 60) { tries++; return loadOlder().then(step); }
            var node = nodeFor(id);
            if (!node) { showError('That message is not available any more.'); return; }
            node.scrollIntoView({ block: 'center', behavior: 'smooth' });
            node.classList.add('msg-flash');
            setTimeout(function () { node.classList.remove('msg-flash'); }, 1800);
        }
        step();
    }

    // ---------------------------------------------------------------- polling
    function updateStatus(id, status) {
        var m = messages.get(id);
        if (!m || m.status === status) return;
        m.status = status;
        var node = nodeFor(id);
        if (!node) return;
        var tick = node.querySelector('.msg-status');
        if (tick) {
            tick.textContent = TICKS[status]; tick.title = TICK_TEXT[status];
            tick.setAttribute('aria-label', TICK_TEXT[status]);
            tick.classList.toggle('is-seen', status === 'seen');
        }
    }

    function applyDeleted(id) {
        var m = messages.get(id);
        if (!m || m.deleted) return;
        m.deleted = true; m.body = null; m.media_url = null; m.status = null;
        replaceNode(m);
        messages.forEach(function (other) {
            if (other.reply && other.reply.id === id && !other.reply.deleted) {
                other.reply = { id: id, deleted: true };
                replaceNode(other);
            }
        });
    }

    function setTyping(on) {
        if (on) {
            el.typing.textContent = PARTNER + ' is typing\u2026';
            var near = isNearBottom();
            el.typing.hidden = false;
            if (near) scrollBottom();
        } else {
            el.typing.hidden = true;
        }
    }

    function setPresence(p) {
        var text = '';
        el.presence.classList.toggle('is-online', p.state === 'online');
        if (p.state === 'online') text = 'Online';
        else if (p.state === 'recent') text = 'Last seen recently';
        else if (p.last_seen_at) {
            var d = new Date(p.last_seen_at);
            var time = timeFmt.format(d);
            var label = dayLabel(d);
            text = 'Last seen ' + (label === 'Today' || label === 'Yesterday'
                ? label.toLowerCase() + ' at ' + time
                : d.toLocaleDateString([], { day: 'numeric', month: 'short' }) + ' at ' + time);
        } else text = 'Offline';
        el.presence.textContent = text;
    }

    function markSeen() {
        if (document.hidden) return;
        var top = 0;
        messages.forEach(function (m) { if (!m.mine && !m.deleted && m.id > top) top = m.id; });
        if (!top || top <= lastSeenSent) return;
        lastSeenSent = top;
        api('/chat/seen', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ up_to_id: top }) })
            .catch(function () { lastSeenSent = 0; });
    }

    function poll() {
        api('/chat/poll?after_id=' + pollCursor).then(function (data) {
            var near = isNearBottom();
            var gotNew = false;
            data.messages.forEach(function (m) {
                pollCursor = Math.max(pollCursor, m.id);
                if (!messages.has(m.id)) { remember(m); appendNode(m); gotNew = true; }
            });
            data.statuses.forEach(function (s) { updateStatus(s.id, s.status); });
            data.deleted_ids.forEach(applyDeleted);
            setTyping(data.typing);
            setPresence(data.presence);
            if (gotNew) { if (near) scrollBottom(); markSeen(); }
        }).catch(function () { /* short network problem: just try again */ }).then(schedule);
    }
    function schedule() {
        clearTimeout(pollTimer);
        pollTimer = setTimeout(poll, document.hidden ? 15000 : 3000);
    }
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) { clearTimeout(pollTimer); poll(); markSeen(); }
    });
    window.addEventListener('focus', markSeen);

    // ---------------------------------------------------------------- sending
    function lockSend(on) { el.send.disabled = on; }
    function addOwn(m) {
        if (messages.has(m.id)) return;
        remember(m); appendNode(m); scrollBottom();
    }

    function sendText() {
        var body = el.input.value.trim();
        if (!body) return Promise.resolve();
        lockSend(true);
        return api('/chat/send', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ body: body, reply_to_id: replyTo ? replyTo.id : null })
        }).then(function (data) {
            el.input.value = ''; autosize(); clearReply(); addOwn(data.message);
        }).catch(function (e) { showError(e.message); }).then(function () { lockSend(false); });
    }

    function sendPending() {
        if (!pending) return Promise.resolve();
        var fd = new FormData();
        fd.append('kind', pending.kind);
        fd.append('file', pending.blob, pending.kind === 'voice' ? 'voice.' + pending.ext : 'photo.jpg');
        if (pending.kind === 'voice') fd.append('duration_ms', String(Math.round(pending.durationMs)));
        if (replyTo) fd.append('reply_to_id', String(replyTo.id));
        lockSend(true);
        return api('/chat/send-media', { method: 'POST', body: fd }).then(function (data) {
            clearPending(); clearReply(); addOwn(data.message);
        }).catch(function (e) { showError(e.message); }).then(function () { lockSend(false); });
    }

    el.form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (rec) return;
        if (pending) sendPending(); else sendText();
    });

    var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    el.input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey && !coarse) { e.preventDefault(); el.form.requestSubmit(); }
    });
    function autosize() {
        el.input.style.height = 'auto';
        el.input.style.height = Math.min(el.input.scrollHeight, 120) + 'px';
    }
    el.input.addEventListener('input', function () {
        autosize();
        var now = Date.now();
        if (el.input.value && now - lastTypingPing > 3000) {           // at most one ping / 3 s
            lastTypingPing = now;
            api('/chat/typing', { method: 'POST' }).catch(function () {});
        }
    });

    // ---------------------------------------------------------------- reply / delete
    function previewOf(m) {
        if (m.kind === 'image') return 'Photo';
        if (m.kind === 'voice') return 'Voice message';
        return (m.body || '').replace(/\s+/g, ' ').slice(0, 80);
    }
    function setReply(m) {
        replyTo = m;
        el.replyWho.textContent = 'Replying to ' + (m.mine ? 'yourself' : PARTNER);
        el.replyPreview.textContent = previewOf(m);
        el.replyBar.hidden = false;
        el.input.focus();
    }
    function clearReply() { replyTo = null; el.replyBar.hidden = true; }
    el.replyCancel.addEventListener('click', clearReply);

    function deleteMessage(m) {
        if (!confirm('Delete this message for both of you?')) return;
        api('/chat/' + m.id + '/delete', { method: 'POST' }).then(function () { applyDeleted(m.id); })
            .catch(function (e) { showError(e.message); });
    }

    // ---------------------------------------------------------------- pending bar (photo / voice preview + recording)
    function clearPending() {
        if (pending && pending.url) URL.revokeObjectURL(pending.url);
        pending = null; el.pending.hidden = true; el.pending.replaceChildren();
    }
    function showPending(p) {
        clearPending();
        pending = p;
        el.pending.replaceChildren();
        var preview;
        if (p.kind === 'image') { preview = document.createElement('img'); preview.alt = 'Photo preview'; preview.src = p.url; }
        else { preview = document.createElement('audio'); preview.controls = true; preview.src = p.url; }
        var actions = div('chat-pending-actions');
        var send = btn('btn btn-primary', 'Send');
        var discard = btn('btn btn-ghost', 'Discard');
        send.addEventListener('click', sendPending);
        discard.addEventListener('click', clearPending);
        actions.appendChild(send); actions.appendChild(discard);
        el.pending.appendChild(preview); el.pending.appendChild(actions);
        el.pending.hidden = false;
    }

    // ---- photo
    el.attach.addEventListener('click', function () { if (!rec) el.imageInput.click(); });
    var IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

    function shrinkImage(file) {
        if (file.type === 'image/gif' || file.size <= 1.5 * 1024 * 1024 || !window.createImageBitmap) return Promise.resolve(file);
        return createImageBitmap(file).then(function (bmp) {
            var scale = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
            var canvas = document.createElement('canvas');
            canvas.width = Math.round(bmp.width * scale); canvas.height = Math.round(bmp.height * scale);
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
            return new Promise(function (resolve) {
                canvas.toBlob(function (blob) { resolve(blob && blob.size < file.size ? blob : file); }, 'image/jpeg', 0.85);
            });
        }).catch(function () { return file; });
    }
    el.imageInput.addEventListener('change', function () {
        var file = el.imageInput.files[0];
        el.imageInput.value = '';
        if (!file) return;
        if (IMAGE_TYPES.indexOf(file.type) === -1) { showError('Please choose a JPG, PNG, GIF or WebP photo.'); return; }
        shrinkImage(file).then(function (blob) {
            if (blob.size > 5 * 1024 * 1024) { showError('That photo is too large (max 5 MB).'); return; }
            showPending({ kind: 'image', blob: blob, url: URL.createObjectURL(blob) });
        });
    });

    // ---- voice
    var canRecord = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder && window.isSecureContext);
    if (!canRecord) {
        el.mic.disabled = true;
        el.mic.title = 'Voice messages need a secure (https or localhost) page and a supported browser.';
    }

    function extFor(mime) { return /ogg/.test(mime) ? 'ogg' : /mp4|aac/.test(mime) ? 'mp4' : 'webm'; }

    function renderRecordingBar() {
        el.pending.replaceChildren();
        var label = document.createElement('div');
        var dotEl = document.createElement('span'); dotEl.className = 'rec-dot';
        var time = document.createElement('span'); time.id = 'recTime'; time.textContent = '0:00';
        label.appendChild(dotEl); label.appendChild(time);
        var actions = div('chat-pending-actions');
        var stop = btn('btn btn-primary', 'Stop');
        var cancel = btn('btn btn-ghost', 'Cancel');
        stop.addEventListener('click', function () { stopRecording(true); });
        cancel.addEventListener('click', function () { stopRecording(false); });
        actions.appendChild(stop); actions.appendChild(cancel);
        el.pending.appendChild(label); el.pending.appendChild(actions);
        el.pending.hidden = false;
    }

    function startRecording() {
        if (rec || pending) return;
        navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
            var mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
                .find(function (t) { return MediaRecorder.isTypeSupported(t); });
            var recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
            rec = { recorder: recorder, stream: stream, chunks: [], startedAt: Date.now(), mime: recorder.mimeType || mime || 'audio/webm', save: false };
            recorder.ondataavailable = function (e) { if (e.data && e.data.size) rec.chunks.push(e.data); };
            recorder.onstop = finishRecording;
            recorder.start();
            renderRecordingBar();
            recTimer = setInterval(function () {
                var ms = Date.now() - rec.startedAt;
                var t = $('recTime'); if (t) t.textContent = fmtDur(ms);
                if (ms >= 5 * 60 * 1000) stopRecording(true);        // 5 minute limit
            }, 250);
        }).catch(function () { showError('Microphone permission is needed to record a voice message.'); });
    }
    function stopRecording(save) {
        if (!rec) return;
        rec.save = save;
        clearInterval(recTimer);
        if (rec.recorder.state !== 'inactive') rec.recorder.stop();
        rec.stream.getTracks().forEach(function (t) { t.stop(); });
    }
    function finishRecording() {
        var r = rec; rec = null;
        el.pending.hidden = true; el.pending.replaceChildren();
        if (!r || !r.save) return;
        var duration = Date.now() - r.startedAt;
        var blob = new Blob(r.chunks, { type: r.mime });
        if (duration < 700 || !blob.size) { showError('That recording was too short.'); return; }
        showPending({ kind: 'voice', blob: blob, url: URL.createObjectURL(blob), durationMs: duration, ext: extFor(r.mime) });
    }
    el.mic.addEventListener('click', function () { if (canRecord) startRecording(); });

    // ---------------------------------------------------------------- photo viewer
    function openViewer(src) {
        var box = div('chat-viewer'); var img = document.createElement('img'); img.src = src; img.alt = 'Photo';
        box.appendChild(img);
        function close() { box.remove(); document.removeEventListener('keydown', onKey); }
        function onKey(e) { if (e.key === 'Escape') close(); }
        box.addEventListener('click', close);
        document.addEventListener('keydown', onKey);
        document.body.appendChild(box);
    }

    // ---------------------------------------------------------------- search
    el.searchBtn.addEventListener('click', function () {
        el.search.hidden = !el.search.hidden;
        if (!el.search.hidden) el.searchInput.focus();
    });
    var searchTimer = null;
    el.searchInput.addEventListener('input', function () {
        clearTimeout(searchTimer);
        var q = el.searchInput.value.trim();
        if (q.length < 2) { el.searchResults.replaceChildren(); return; }
        searchTimer = setTimeout(function () {
            api('/chat/search?q=' + encodeURIComponent(q)).then(function (data) {
                el.searchResults.replaceChildren();
                if (!data.results.length) {
                    var none = div('chat-search-empty'); none.textContent = 'No messages found.'; el.searchResults.appendChild(none); return;
                }
                data.results.forEach(function (r) {
                    var hit = btn('chat-search-hit', r.snippet);
                    var small = document.createElement('small');
                    small.textContent = (r.mine ? 'You' : PARTNER) + ' \u00B7 ' + new Date(r.created_at).toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
                    hit.appendChild(small);
                    hit.addEventListener('click', function () { el.search.hidden = true; jumpTo(r.id); });
                    el.searchResults.appendChild(hit);
                });
            }).catch(function (e) { showError(e.message); });
        }, 300);
    });

    el.older.addEventListener('click', loadOlder);

    // ---------------------------------------------------------------- keyboard-safe height on phones
    function fitHeight() {
        var vv = window.visualViewport;
        var viewH = vv ? vv.height : window.innerHeight;
        var offsetTop = vv ? vv.offsetTop : 0;
        var top = app.getBoundingClientRect().top - offsetTop;
        var isPhone = window.matchMedia('(max-width: 600px)').matches;
        app.style.height = Math.max(320, viewH - Math.max(top, 0) - (isPhone ? 0 : 8)) + 'px';
        if (isNearBottom()) scrollBottom();
    }
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', fitHeight);
        window.visualViewport.addEventListener('scroll', fitHeight);
    }
    window.addEventListener('resize', fitHeight);

    // ---------------------------------------------------------------- start
    fitHeight();
    autosize();
    loadInitial().then(function () { fitHeight(); poll(); });
})();
/* Phase 6: keeps the bell badge fresh on every page and shows times in the user's own time zone. */
(function () {
    'use strict';

    // ---- local time for <time data-utc="..."> ----
    function relative(date) {
        var diff = (Date.now() - date.getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return Math.floor(diff / 60) + ' min ago';
        var now = new Date();
        var time = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        if (date.toDateString() === now.toDateString()) return 'Today, ' + time;
        var yesterday = new Date(now.getTime() - 86400000);
        if (date.toDateString() === yesterday.toDateString()) return 'Yesterday, ' + time;
        return date.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' }) + ', ' + time;
    }
    document.querySelectorAll('time[data-utc]').forEach(function (node) {
        var d = new Date(node.dataset.utc);
        if (!isNaN(d)) node.textContent = relative(d);
    });

    // ---- bell badge + chat dot ----
    var badge = document.getElementById('bellBadge');
    var dot = document.getElementById('chatDot');
    if (!badge && !dot) return;

    function apply(data) {
        if (badge) {
            badge.textContent = data.unread > 99 ? '99+' : String(data.unread);
            badge.hidden = !data.unread;
        }
        if (dot) dot.hidden = !data.chat_unread;
    }

    function refresh() {
        if (document.hidden) return;
        fetch('/notifications/summary', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (res) {
                var type = res.headers.get('content-type') || '';
                if (!res.ok || res.redirected || type.indexOf('json') === -1) return null;
                return res.json();
            })
            .then(function (data) { if (data) apply(data); })
            .catch(function () { /* offline or server sleeping: try again next time */ });
    }

    setInterval(refresh, 30000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
    refresh();
})();
