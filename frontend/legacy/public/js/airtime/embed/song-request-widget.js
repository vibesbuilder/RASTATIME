/*
 * RASTATIME 2026-06-07 — Song Request Widget runtime (table view).
 *
 * Vanilla JS (no jQuery — runs inside its own iframe).  On load it
 * fetches the requestable pool from GET /api/v2/song-requests/search
 * (no query = the listing, capped at 500) and renders a scrollable,
 * non-paginated table: cover | artist / title | "Request" button.  The
 * button POSTs {file_id} to /api/v2/song-requests and shows a message
 * based on the HTTP code (201 ok, 409 duplicate, 429 rate-limited, else
 * error).
 *
 * RASTATIME 2026-11-13 - search box: from 2 characters (the API's
 * SEARCH_MIN_CHARS) the search runs over the whole pool, 300 ms after the
 * last keystroke (the search endpoint allows 60 calls a minute per IP);
 * an older answer arriving after a newer one is dropped.  Fewer than 2
 * characters show the listing again (kept from the first load).  A note
 * says when the listing or the matches are cut (`limit` in the answer).
 * The answer to a request appears in a row under the track clicked: with
 * the self-sizing frame the whole list is the page, and a status line at
 * the end of 500 rows was out of sight.
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

    var SEARCH_MIN_CHARS = 2;
    var SEARCH_DELAY_MS = 300;

    var body = document.body;
    if (!body || !body.classList.contains('sr-widget')) {
        return;
    }
    var rowsEl = body.querySelector('.sr-rows');
    if (!rowsEl) {
        return; // disabled state — no pool configured
    }
    var statusEl = body.querySelector('.sr-status');
    var searchEl = body.querySelector('.sr-search');
    var noteEl = body.querySelector('.sr-note');

    var listUrl = body.getAttribute('data-list-url');
    var submitUrl = body.getAttribute('data-submit-url');
    var coverUrl = body.getAttribute('data-cover-url');
    var total = parseInt(body.getAttribute('data-total'), 10) || 0;

    var L = {
        loading:   body.getAttribute('data-label-loading'),
        noTracks:  body.getAttribute('data-label-no-tracks'),
        request:   body.getAttribute('data-label-request'),
        success:   body.getAttribute('data-label-success'),
        duplicate: body.getAttribute('data-label-duplicate'),
        ratelimit: body.getAttribute('data-label-ratelimit'),
        error:     body.getAttribute('data-label-error'),
        search:    body.getAttribute('data-label-search'),
        noMatches: body.getAttribute('data-label-no-matches'),
        more:      body.getAttribute('data-label-more'),
        refine:    body.getAttribute('data-label-refine')
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

    // 5124 -> "5,124" / "5.124" in the station language (<html lang>)
    function num(n) {
        try {
            return Number(n).toLocaleString(document.documentElement.lang || undefined);
        } catch (e) {
            return String(n);
        }
    }

    // RASTATIME 2026-11-14 - counts travel as tokens (own texts from
    // Widgets -> Song Request use them too): {shown} rows, {total} pool
    function fill(tpl, vals) {
        return String(tpl || '').replace(/\{(shown|total)\}/g, function (m, k) {
            return vals[k] !== undefined ? vals[k] : m;
        });
    }

    function setStatus(msg, kind) {
        statusEl.textContent = msg || '';
        statusEl.className = 'sr-status' + (kind ? ' sr-' + kind : '');
    }

    function setNote(msg) {
        if (noteEl) { noteEl.textContent = msg || ''; }
    }

    var listing = null;   // {results, limit} of the empty query, kept
    var seq = 0;          // newest request; older answers are dropped
    var shownQuery = '';  // query of the list on screen ('' = listing)
    var timer = null;

    function show(results, q, limit) {
        render(results, q);
        if (!results.length) {
            setNote('');
        } else if (q) {
            setNote(limit && results.length >= limit ? fill(L.refine, { shown: num(limit), total: num(total) }) : '');
        } else {
            setNote(total > results.length ? fill(L.more, { shown: num(results.length), total: num(total) }) : '');
        }
    }

    function load(q) {
        var my = ++seq;
        if (!q && listing) {
            show(listing.results, '', listing.limit);
            return;
        }
        setStatus(L.loading, '');
        var url = listUrl + (q ? '?q=' + encodeURIComponent(q) : '');
        fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'omit' })
            .then(function (r) {
                if (r.status === 429) { throw new Error('ratelimit'); }
                if (!r.ok) { throw new Error('http ' + r.status); }
                return r.json();
            })
            .then(function (data) {
                if (my !== seq) { return; }
                var results = (data && data.results) || [];
                var limit = (data && data.limit) || 0;
                if (!q) { listing = { results: results, limit: limit }; }
                show(results, q, limit);
            })
            .catch(function (err) {
                if (my !== seq) { return; }
                setStatus(err && err.message === 'ratelimit' ? L.ratelimit : L.error, 'err');
            });
    }

    function render(results, q) {
        while (rowsEl.firstChild) {
            rowsEl.removeChild(rowsEl.firstChild);
        }
        if (!results.length) {
            setStatus(q ? L.noMatches : L.noTracks, '');
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
            btn.addEventListener('click', function () { submit(t.id, btn, tr); });
            tdBtn.appendChild(btn);
            tr.appendChild(tdBtn);

            rowsEl.appendChild(tr);
        });
    }

    // the answer to a request, in a row right under the track clicked
    function rowMessage(tr, msg, kind) {
        if (!tr.parentNode) {  // the list changed (a search) while the request ran
            setStatus(msg, kind);
            return;
        }
        var old = rowsEl.querySelector('.sr-msg-row');
        if (old) { old.parentNode.removeChild(old); }
        var mr = document.createElement('tr');
        mr.className = 'sr-msg-row';
        var td = document.createElement('td');
        td.colSpan = 3;
        td.className = 'sr-msg sr-' + kind;
        td.setAttribute('role', 'status');
        td.textContent = msg;
        mr.appendChild(td);
        tr.parentNode.insertBefore(mr, tr.nextSibling);
    }

    function submit(fileId, btn, tr) {
        btn.disabled = true;
        setStatus('', '');
        fetch(submitUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            credentials: 'omit',
            body: JSON.stringify({ file_id: fileId })
        }).then(function (r) {
            if (r.status === 201) { rowMessage(tr, L.success, 'ok'); return; }
            if (r.status === 409) { rowMessage(tr, L.duplicate, 'err'); return; }
            if (r.status === 429) { rowMessage(tr, L.ratelimit, 'err'); return; }
            rowMessage(tr, L.error, 'err');
            btn.disabled = false;
        }).catch(function () {
            rowMessage(tr, L.error, 'err');
            btn.disabled = false;
        });
    }

    if (searchEl) {
        if (total > 0 && L.search) {
            searchEl.placeholder = fill(L.search, { total: num(total) });
        }
        var run = function () {
            clearTimeout(timer);
            var q = searchEl.value.trim();
            if (q.length < SEARCH_MIN_CHARS) { q = ''; }
            if (q === shownQuery) { return; }
            shownQuery = q;
            load(q);
        };
        searchEl.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(run, SEARCH_DELAY_MS);
        });
        searchEl.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter') { ev.preventDefault(); run(); }
        });
    }

    load('');
})();
