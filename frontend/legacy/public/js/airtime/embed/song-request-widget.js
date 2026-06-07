/*
 * RASTATIME 2026-06-07 — Song Request Widget runtime (table view).
 *
 * Vanilla JS (no jQuery — runs inside its own iframe).  On load it
 * fetches the whole requestable pool from GET /api/v2/song-requests/
 * search (no query = whole pool) and renders a scrollable, non-paginated
 * table: cover | artist / title | "Request" button.  The button POSTs
 * {file_id} to /api/v2/song-requests and shows a status message based on
 * the HTTP code (201 ok, 409 duplicate, 429 rate-limited, else error).
 *
 * Covers come from /api/track?id=..&return=artwork-64 (only works when
 * "3rd party API" is enabled in settings) and are rendered only for
 * tracks the list endpoint flagged has_artwork.  Tracks without a cover
 * stay text-only: the artwork endpoint answers them with a 0-byte 200
 * (text/html), which leaves an <img> hanging forever — it fires neither
 * load nor error — so we must not create the <img> at all.
 *
 * Track titles in cc_files are stored HTML-escaped (sometimes double-
 * escaped, e.g. "&amp;#8222;"), so entities are decoded twice and
 * inserted only via textContent (never innerHTML -> no markup injection).
 *
 * fetch uses credentials:'omit' — the endpoints are public, need no
 * cookie, and that sidesteps any session/CSRF interaction.
 */
(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('sr-widget')) {
        return;
    }
    var rowsEl = body.querySelector('.sr-rows');
    if (!rowsEl) {
        return; // disabled state — no pool configured
    }
    var statusEl = body.querySelector('.sr-status');

    var listUrl = body.getAttribute('data-list-url');
    var submitUrl = body.getAttribute('data-submit-url');
    var coverUrl = body.getAttribute('data-cover-url');

    var L = {
        loading:   body.getAttribute('data-label-loading'),
        noTracks:  body.getAttribute('data-label-no-tracks'),
        request:   body.getAttribute('data-label-request'),
        success:   body.getAttribute('data-label-success'),
        duplicate: body.getAttribute('data-label-duplicate'),
        ratelimit: body.getAttribute('data-label-ratelimit'),
        error:     body.getAttribute('data-label-error')
    };

    // Decode HTML entities (cc_files titles can be double-escaped). Plain
    // string out; callers insert via textContent only.
    function decodeEntities(s) {
        if (!s) { return ''; }
        var ta = document.createElement('textarea');
        ta.innerHTML = s;
        ta.innerHTML = ta.value;
        return ta.value;
    }

    function setStatus(msg, kind) {
        statusEl.textContent = msg || '';
        statusEl.className = 'sr-status' + (kind ? ' sr-' + kind : '');
    }

    function load() {
        setStatus(L.loading, '');
        fetch(listUrl, { headers: { 'Accept': 'application/json' }, credentials: 'omit' })
            .then(function (r) { return r.json(); })
            .then(function (data) { render((data && data.results) || []); })
            .catch(function () { setStatus(L.error, 'err'); });
    }

    function render(results) {
        while (rowsEl.firstChild) {
            rowsEl.removeChild(rowsEl.firstChild);
        }
        if (!results.length) {
            setStatus(L.noTracks, '');
            return;
        }
        setStatus('', '');
        results.forEach(function (t) {
            var artist = decodeEntities(t.artist);
            var title = decodeEntities(t.title) || '(untitled)';

            var tr = document.createElement('tr');

            // cover
            var tdCover = document.createElement('td');
            tdCover.className = 'sr-cover-cell';
            if (coverUrl && t.has_artwork) {
                var img = document.createElement('img');
                img.className = 'sr-cover';
                // No loading='lazy': a lazy <img> inserted via JS can stay
                // complete=false indefinitely inside an iframe (the load
                // never resolves). Covers are tiny artwork-64 thumbnails and
                // only render for has_artwork tracks, so eager load is fine.
                img.alt = '';
                img.src = coverUrl + '?id=' + encodeURIComponent(t.id) + '&return=artwork-64';
                // Defensive only: the list already filters to has_artwork
                // tracks, but hide the <img> if the cover was removed
                // between pool sync and load (HTTP error or empty body).
                img.onerror = function () { this.style.display = 'none'; };
                img.onload = function () { if (!this.naturalWidth) { this.style.display = 'none'; } };
                tdCover.appendChild(img);
            }
            tr.appendChild(tdCover);

            // artist (bold) + title (muted, below)
            var tdTrack = document.createElement('td');
            tdTrack.className = 'sr-track';
            var line1 = document.createElement('div');
            line1.className = 'sr-track-artist';
            line1.textContent = artist || title;
            tdTrack.appendChild(line1);
            if (artist) {
                var line2 = document.createElement('div');
                line2.className = 'sr-track-title';
                line2.textContent = title;
                tdTrack.appendChild(line2);
            }
            tr.appendChild(tdTrack);

            // request button
            var tdBtn = document.createElement('td');
            tdBtn.className = 'sr-btn-cell';
            var btn = document.createElement('button');
            btn.className = 'sr-btn';
            btn.type = 'button';
            btn.textContent = L.request;
            btn.addEventListener('click', function () { submit(t.id, btn); });
            tdBtn.appendChild(btn);
            tr.appendChild(tdBtn);

            rowsEl.appendChild(tr);
        });
    }

    function submit(fileId, btn) {
        btn.disabled = true;
        setStatus('', '');
        fetch(submitUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            credentials: 'omit',
            body: JSON.stringify({ file_id: fileId })
        }).then(function (r) {
            if (r.status === 201) { setStatus(L.success, 'ok'); return; }
            if (r.status === 409) { setStatus(L.duplicate, 'err'); return; }
            if (r.status === 429) { setStatus(L.ratelimit, 'err'); return; }
            setStatus(L.error, 'err');
            btn.disabled = false;
        }).catch(function () {
            setStatus(L.error, 'err');
            btn.disabled = false;
        });
    }

    load();
})();
