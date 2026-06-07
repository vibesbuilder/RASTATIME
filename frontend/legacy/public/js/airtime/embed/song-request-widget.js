/*
 * RASTATIME 2026-06-07 — Song Request Widget runtime.
 *
 * Vanilla JS (no jQuery — runs inside its own iframe).  Behaviour:
 *   1. Debounced search box queries GET /api/v2/song-requests/search,
 *      restricted server-side to the operator's Requestable Pool.
 *   2. Each result renders title + artist + a "Request" button.
 *   3. The button POSTs {file_id} to /api/v2/song-requests and shows a
 *      status message based on the HTTP code (201 ok, 409 duplicate,
 *      429 rate-limited, anything else generic error).
 *
 * Track titles in cc_files are stored HTML-escaped (and sometimes
 * double-escaped, e.g. "&amp;#8222;"), so we decode entities twice
 * before inserting them as text — via textContent only, never
 * innerHTML, so a crafted title can never inject markup.
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
    var searchEl = body.querySelector('.sr-search');
    if (!searchEl) {
        return; // disabled state — no pool configured
    }
    var resultsEl = body.querySelector('.sr-results');
    var statusEl = body.querySelector('.sr-status');

    var searchUrl = body.getAttribute('data-search-url');
    var submitUrl = body.getAttribute('data-submit-url');
    var minChars = parseInt(body.getAttribute('data-min-chars') || '2', 10);

    var L = {
        searching: body.getAttribute('data-label-searching'),
        noResults: body.getAttribute('data-label-no-results'),
        minChars:  body.getAttribute('data-label-min-chars'),
        request:   body.getAttribute('data-label-request'),
        success:   body.getAttribute('data-label-success'),
        duplicate: body.getAttribute('data-label-duplicate'),
        ratelimit: body.getAttribute('data-label-ratelimit'),
        error:     body.getAttribute('data-label-error')
    };

    // Decode HTML entities. cc_files titles can be double-escaped
    // ("&amp;#8222;" → "&#8222;" → "„"), so we run the textarea decode
    // twice. Returns a plain string; callers insert it via textContent.
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

    function clearResults() {
        while (resultsEl.firstChild) {
            resultsEl.removeChild(resultsEl.firstChild);
        }
    }

    var debounceTimer = null;
    var lastQuery = '';

    searchEl.addEventListener('input', function () {
        var q = searchEl.value.trim();
        if (debounceTimer) { clearTimeout(debounceTimer); }
        if (q.length < minChars) {
            clearResults();
            setStatus(q.length ? L.minChars : '', '');
            return;
        }
        debounceTimer = setTimeout(function () { doSearch(q); }, 300);
    });

    function doSearch(q) {
        lastQuery = q;
        setStatus(L.searching, '');
        fetch(searchUrl + '?q=' + encodeURIComponent(q), {
            headers: { 'Accept': 'application/json' },
            credentials: 'omit'
        }).then(function (r) {
            return r.json();
        }).then(function (data) {
            if (q !== lastQuery) { return; } // a newer query already fired
            renderResults((data && data.results) || []);
        }).catch(function () {
            setStatus(L.error, 'err');
        });
    }

    function renderResults(results) {
        clearResults();
        if (!results.length) {
            setStatus(L.noResults, '');
            return;
        }
        setStatus('', '');
        results.forEach(function (t) {
            var li = document.createElement('li');
            li.className = 'sr-item';

            var meta = document.createElement('div');
            meta.className = 'sr-item-meta';

            var title = document.createElement('div');
            title.className = 'sr-item-title';
            title.textContent = decodeEntities(t.title) || '(untitled)';
            meta.appendChild(title);

            var artistText = decodeEntities(t.artist);
            if (artistText) {
                var artist = document.createElement('div');
                artist.className = 'sr-item-artist';
                artist.textContent = artistText;
                meta.appendChild(artist);
            }

            var btn = document.createElement('button');
            btn.className = 'sr-btn';
            btn.type = 'button';
            btn.textContent = L.request;
            btn.addEventListener('click', function () { submit(t.id, btn); });

            li.appendChild(meta);
            li.appendChild(btn);
            resultsEl.appendChild(li);
        });
    }

    function submit(fileId, btn) {
        btn.disabled = true;
        setStatus('', '');
        fetch(submitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'omit',
            body: JSON.stringify({ file_id: fileId })
        }).then(function (r) {
            if (r.status === 201) {
                setStatus(L.success, 'ok');
                return;
            }
            if (r.status === 409) { setStatus(L.duplicate, 'err'); return; }
            if (r.status === 429) { setStatus(L.ratelimit, 'err'); return; }
            setStatus(L.error, 'err');
            btn.disabled = false;
        }).catch(function () {
            setStatus(L.error, 'err');
            btn.disabled = false;
        });
    }
})();
