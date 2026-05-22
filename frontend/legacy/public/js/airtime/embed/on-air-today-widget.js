/*
 * RASTATIME 2026-05-22 — On-Air-Today widget runtime.
 *
 * Sibling of now-playing-widget.js / shows-list-widget.js, kept
 * separate so each widget has its own narrow surface area.
 *
 * Behaviour summary:
 *
 *   1. Server-side initial render in on-air-today.phtml — every
 *      row ships with absolute ISO-8601 start/end timestamps on
 *      data-attributes, plus a class on the currently-airing row.
 *
 *   2. Every second the tick re-renders the time cells so the
 *      visible "HH:MM - HH:MM" stays in sync with the browser's
 *      locale, and notices when the currently-airing row's end
 *      has passed — triggering an early refresh so the bold
 *      highlight migrates to the next row within ~1 s instead
 *      of waiting out the cache TTL.
 *
 *   3. Every cache-TTL seconds the script polls /Embed/on-air-
 *      today-data for fresh JSON and rebuilds the <ul>.
 *
 * Vanilla JS (no jQuery) — the iframe runs in isolation.
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-on-air-today')) {
        return;
    }

    var dataUrl    = body.getAttribute('data-data-url')  || '/Embed/on-air-today-data';
    var cacheTtlMs = parseInt(body.getAttribute('data-cache-ttl') || '60', 10) * 1000;
    var isToday    = body.getAttribute('data-is-today') === '1';
    var labels = {
        empty: body.getAttribute('data-label-empty') || 'No shows on air today'
    };

    var failedPolls = 0;
    var MAX_FAILED_POLLS = 3;

    // Watch the currently-airing row's end-time so we can fire an
    // early refresh as soon as the bold highlight needs to move
    // to the next row.  Recomputed after every poll.
    var currentEndIso = null;

    function pad2(n) {
        return n < 10 ? '0' + n : String(n);
    }

    /*
     * Format a start–end pair as "H:MM - H:MM".  Hour drops its
     * leading zero per operator convention 2026-05-22 v10 (9:00
     * not 09:00); minute stays 2-digit so the colon-suffix is
     * always there.  Degrades gracefully when either bound is
     * missing.
     */
    function fmtTimeRange(startIso, endIso) {
        function fmt(iso) {
            if (!iso) { return ''; }
            var d = new Date(iso);
            if (isNaN(d.getTime())) { return iso; }
            return d.getHours() + ':' + pad2(d.getMinutes());
        }
        var a = fmt(startIso);
        var b = fmt(endIso);
        if (!a && !b) { return ''; }
        if (!a) { return '… - ' + b; }
        if (!b) { return a + ' - …'; }
        return a + ' - ' + b;
    }

    /*
     * Refresh the visible text of every time cell from its
     * data-starts / data-ends attributes.  Touches no other DOM
     * so a network blip never wipes the names or links.
     */
    function paintTimes() {
        var cells = document.querySelectorAll('.np-on-air-time');
        for (var i = 0; i < cells.length; i++) {
            var s = cells[i].getAttribute('data-starts');
            var e = cells[i].getAttribute('data-ends');
            cells[i].textContent = fmtTimeRange(s, e);
        }
    }

    /*
     * Rebuild the <ul> rows from a fresh shows array.  Recreate
     * rather than diff — the widget rarely shows more than ~6
     * rows and the simpler replace is easier to reason about than
     * a keyed reconciler.
     */
    function rebuildList(shows) {
        var ul = document.querySelector('[data-np="list"]');
        if (!ul) { return; }

        while (ul.firstChild) {
            ul.removeChild(ul.firstChild);
        }

        if (!shows || shows.length === 0) {
            var li = document.createElement('li');
            li.className = 'np-list-empty';
            li.setAttribute('data-np', 'empty');
            var label = document.createElement('span');
            label.className = 'np-name';
            label.textContent = labels.empty;
            li.appendChild(label);
            ul.appendChild(li);
            currentEndIso = null;
            return;
        }

        currentEndIso = null;
        for (var i = 0; i < shows.length; i++) {
            var s = shows[i];
            var row = document.createElement('li');
            row.className = 'np-list-row np-on-air-row';
            if (s.isCurrent) {
                row.className += ' np-row-current';
                currentEndIso = s.ends || null;
            }

            var timeSpan = document.createElement('span');
            timeSpan.className = 'np-on-air-time';
            timeSpan.setAttribute('data-starts', s.starts || '');
            timeSpan.setAttribute('data-ends',   s.ends   || '');
            row.appendChild(timeSpan);

            var nameSpan = document.createElement('span');
            nameSpan.className = 'np-on-air-name np-name';
            if (s.url) {
                var a = document.createElement('a');
                a.href = s.url;
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                a.textContent = s.name || '';
                nameSpan.appendChild(a);
            } else {
                nameSpan.textContent = s.name || '';
            }
            row.appendChild(nameSpan);

            ul.appendChild(row);
        }

        paintTimes();
    }

    /*
     * Per-second tick.  Two responsibilities:
     *   - Re-render visible time cells (in case the user changed
     *     OS locale mid-session, or the date rolls over).
     *   - When the currently-airing row's end has passed, fire
     *     an immediate poll so the bold highlight migrates to
     *     the next row without waiting out the cache TTL.  Only
     *     active for today's view; pinned-day views never have
     *     a "current" row by definition.
     */
    function tick() {
        paintTimes();

        if (isToday && currentEndIso) {
            var endMs = new Date(currentEndIso).getTime();
            var nowMs = Date.now();
            if (endMs - nowMs < 0 && endMs - nowMs > -2000) {
                // Detach the watch immediately so we don't re-fire
                // every tick until the next poll lands.
                currentEndIso = null;
                pollOnce();
            }
        }
    }

    /*
     * Seed the current-end watcher from the server-rendered DOM
     * so the early-poll mechanism is active before the first
     * refresh round-trip completes.
     */
    function seedCurrentEnd() {
        if (!isToday) { return; }
        var row = document.querySelector('.np-on-air-row.np-row-current .np-on-air-time');
        if (row) {
            currentEndIso = row.getAttribute('data-ends') || null;
        }
    }

    function pollOnce() {
        fetch(dataUrl, { credentials: 'omit', cache: 'default' })
            .then(function (r) {
                if (!r.ok) { throw new Error('HTTP ' + r.status); }
                return r.json();
            })
            .then(function (payload) {
                failedPolls = 0;
                body.classList.remove('np-stale');
                if (payload.labels && payload.labels.noOnAirToday) {
                    labels.empty = payload.labels.noOnAirToday;
                }
                rebuildList(payload.shows || []);
            })
            .catch(function () {
                failedPolls++;
                if (failedPolls >= MAX_FAILED_POLLS) {
                    body.classList.add('np-stale');
                }
            });
    }

    seedCurrentEnd();
    paintTimes();
    setInterval(tick, 1000);

    var jitter = 0.9 + Math.random() * 0.2;
    setInterval(pollOnce, Math.max(10000, cacheTtlMs * jitter));
})();
