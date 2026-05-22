/*
 * RASTATIME 2026-05-22 — Next-Shows / Latest-Shows Widget runtime.
 *
 * Sibling of now-playing-widget.js but for the LIST widgets: no
 * per-second countdown, just a periodic refresh of the rendered
 * rows when the JSON endpoint has new data.
 *
 * Behaviour summary (mirrors the two-line widget so an operator
 * troubleshooting one widget can apply the same instincts to the
 * other):
 *
 *   1. Server-side initial render in shows-list.phtml — every row
 *      ships with absolute ISO-8601 start/end timestamps in
 *      `data-starts` / `data-ends` attributes so the first paint
 *      is meaningful even before any JS runs.
 *
 *   2. Every second the dateRender pass converts those timestamps
 *      to the visitor's locale ("Tue 21 May" / "18:00 - 19:00"),
 *      so the visible strings stay in sync with the browser's
 *      timezone display preference even though the underlying
 *      data is timezone-stamped server-side.
 *
 *   3. Every cache-TTL seconds the script polls /Embed/shows-
 *      data?direction=...&show_id=... for fresh JSON and rebuilds
 *      the <li> rows from scratch.  Browser HTTP cache means N
 *      embeds across the public site share one round trip.
 *
 *   4. When the topmost (next-shows) or bottommost (latest-shows)
 *      instance's start-time slides past the current wall clock,
 *      a single extra poll fires immediately so the list flips
 *      to the new window with sub-second latency instead of
 *      waiting out the cache TTL.
 *
 * Vanilla JS (no jQuery) — the iframe runs in isolation and we
 * don't want to drag a 90 KB library along for a date formatter
 * and a setInterval.
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-shows-list')) {
        return;
    }

    var direction  = body.getAttribute('data-direction') || 'next'; // 'next'|'latest'
    var dataUrl    = body.getAttribute('data-data-url')  || '/Embed/shows-data';
    var cacheTtlMs = parseInt(body.getAttribute('data-cache-ttl') || '60', 10) * 1000;
    var labels = {
        empty: body.getAttribute('data-label-empty') ||
               (direction === 'latest' ? 'No past shows' : 'No upcoming shows')
    };

    var failedPolls = 0;
    var MAX_FAILED_POLLS = 3;

    // Track the earliest future / latest past instance start-time
    // we currently have in the DOM, so the per-second tick can
    // notice when the list has effectively gone stale and fire an
    // early refresh.
    var watchedBoundaryIso = null;

    /*
     * Pad a number to two digits ("7" → "07").  Used in date / time
     * formatting; pulled out to a helper because PHP's str_pad
     * doesn't exist here.
     */
    function pad2(n) {
        return n < 10 ? '0' + n : String(n);
    }

    /*
     * Format an ISO timestamp as "Tue 21 May" in the visitor's
     * locale.  Short weekday + day-of-month + short month — enough
     * for the operator to see the row at a glance without eating
     * widget width.
     */
    function fmtDate(iso) {
        if (!iso) { return ''; }
        var d = new Date(iso);
        if (isNaN(d.getTime())) { return iso; }
        try {
            return d.toLocaleDateString(undefined, {
                weekday: 'short',
                day:     'numeric',
                month:   'short'
            });
        } catch (e) {
            // Older browsers without `toLocaleDateString` options
            // support fall back to a fixed English format.
            var WEEKDAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
            var MONTHS   = ['Jan','Feb','Mar','Apr','May','Jun',
                            'Jul','Aug','Sep','Oct','Nov','Dec'];
            return WEEKDAYS[d.getDay()] + ' ' + d.getDate()
                 + ' ' + MONTHS[d.getMonth()];
        }
    }

    /*
     * Format a start–end pair as "HH:MM - HH:MM".  Degrades
     * gracefully when either end is missing.
     */
    function fmtTimeRange(startIso, endIso) {
        function fmt(iso) {
            if (!iso) { return ''; }
            var d = new Date(iso);
            if (isNaN(d.getTime())) { return iso; }
            return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
        }
        var a = fmt(startIso);
        var b = fmt(endIso);
        if (!a && !b) { return ''; }
        if (!a) { return '… - ' + b; }
        if (!b) { return a + ' - …'; }
        return a + ' - ' + b;
    }

    /*
     * Re-render the visible text of every list row from the
     * `data-starts` / `data-ends` attributes already in the DOM.
     * Cheap enough to run every second; never touches structural
     * markup so a network blip does not erase the list.
     */
    function paintRows() {
        var rows = document.querySelectorAll('.np-list-row');
        for (var i = 0; i < rows.length; i++) {
            var dateCell = rows[i].querySelector('.np-list-date');
            var timeCell = rows[i].querySelector('.np-list-time');
            if (dateCell) {
                var ds = dateCell.getAttribute('data-starts');
                dateCell.textContent = fmtDate(ds);
            }
            if (timeCell) {
                var ts = timeCell.getAttribute('data-starts');
                var te = timeCell.getAttribute('data-ends');
                timeCell.textContent = fmtTimeRange(ts, te);
            }
        }
    }

    /*
     * Re-paint the title cell (operator may have renamed the show
     * since the iframe first loaded — refresh picks it up).
     */
    function paintTitle(showMeta) {
        var title = document.querySelector('[data-np="title"]');
        if (!title) { return; }
        if (showMeta && showMeta.name) {
            title.textContent = showMeta.name;
        } else {
            title.textContent = labels.empty;
        }
    }

    /*
     * Rebuild the <ul> rows from a fresh instances array.  We
     * recreate the rows from scratch rather than diff because the
     * widget rarely shows more than ~10 rows and the simpler
     * replace is easier to reason about than a keyed reconciler.
     */
    function rebuildList(instances) {
        var ul = document.querySelector('[data-np="list"]');
        if (!ul) { return; }

        // Clear existing children
        while (ul.firstChild) {
            ul.removeChild(ul.firstChild);
        }

        if (!instances || instances.length === 0) {
            var li = document.createElement('li');
            li.className = 'np-list-empty';
            li.setAttribute('data-np', 'empty');
            var label = document.createElement('span');
            label.className = 'np-name';
            label.textContent = labels.empty;
            li.appendChild(label);
            ul.appendChild(li);
            watchedBoundaryIso = null;
            return;
        }

        for (var i = 0; i < instances.length; i++) {
            var inst = instances[i];
            var row = document.createElement('li');
            row.className = 'np-list-row';

            var dateSpan = document.createElement('span');
            dateSpan.className = 'np-list-date';
            dateSpan.setAttribute('data-starts', inst.starts || '');
            dateSpan.setAttribute('data-ends',   inst.ends   || '');
            row.appendChild(dateSpan);

            var timeSpan = document.createElement('span');
            timeSpan.className = 'np-list-time';
            timeSpan.setAttribute('data-starts', inst.starts || '');
            timeSpan.setAttribute('data-ends',   inst.ends   || '');
            row.appendChild(timeSpan);

            ul.appendChild(row);
        }

        // Recompute the early-poll boundary: for next-shows we
        // watch the topmost row (the soonest upcoming instance),
        // for latest-shows we watch the bottommost row's end-time
        // since the "latest" window only effectively rolls over
        // when a new instance finishes airing.
        if (direction === 'latest') {
            watchedBoundaryIso = null; // No early-poll trigger needed
        } else {
            watchedBoundaryIso = instances[0].starts || null;
        }

        paintRows();
    }

    /*
     * Per-second tick.  Two responsibilities:
     *   - Re-render the visible text of every row (in case the
     *     wall clock has crossed midnight or the visitor changed
     *     their OS locale).
     *   - Detect when the watched boundary has slid past now and
     *     fire an early poll so a recurring weekly show's row
     *     disappears from the next-shows list within ~1 s of
     *     actually starting.
     */
    function tick() {
        paintRows();

        if (watchedBoundaryIso) {
            var boundaryMs = new Date(watchedBoundaryIso).getTime();
            var nowMs = Date.now();
            if (boundaryMs - nowMs < 0 && boundaryMs - nowMs > -2000) {
                // Detach the watch immediately so we don't re-fire
                // every tick until the next poll lands.
                watchedBoundaryIso = null;
                pollOnce();
            }
        }
    }

    /*
     * Single poll round-trip to the JSON endpoint.
     */
    function pollOnce() {
        fetch(dataUrl, { credentials: 'omit', cache: 'default' })
            .then(function (r) {
                if (!r.ok) { throw new Error('HTTP ' + r.status); }
                return r.json();
            })
            .then(function (payload) {
                failedPolls = 0;
                body.classList.remove('np-stale');
                if (payload.labels) {
                    labels.empty = (direction === 'latest'
                        ? payload.labels.noLatestShows
                        : payload.labels.noNextShows) || labels.empty;
                }
                paintTitle(payload.show);
                rebuildList(payload.instances || []);
            })
            .catch(function () {
                failedPolls++;
                if (failedPolls >= MAX_FAILED_POLLS) {
                    body.classList.add('np-stale');
                }
            });
    }

    // Boot: first paint immediately so the date / time cells are
    // not blank for one second, then the regular cadence.  We
    // also seed `watchedBoundaryIso` from the server-rendered DOM
    // so the early-poll mechanism is active before the first
    // refresh lands.
    (function seedBoundary() {
        if (direction === 'latest') { return; }
        var firstRow = document.querySelector('.np-list-row .np-list-date');
        if (firstRow) {
            watchedBoundaryIso = firstRow.getAttribute('data-starts') || null;
        }
    })();
    paintRows();
    setInterval(tick, 1000);

    var jitter = 0.9 + Math.random() * 0.2;
    setInterval(pollOnce, Math.max(10000, cacheTtlMs * jitter));
})();
