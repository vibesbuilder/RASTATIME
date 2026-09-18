/*
 * RASTATIME 2026-05-22 — Now-Playing Show / Track Widget runtime.
 *
 * Vanilla JS (no jQuery dependency — the widget runs inside its own
 * iframe and we don't want to drag a 90 KB library along for two
 * timer functions).  Works in every browser that supports
 * fetch + Intl.DateTimeFormat (Chrome 42+, Firefox 39+, Safari 10.1+,
 * Edge 14+ — i.e. essentially all live browsers).
 *
 * Behaviour:
 *
 *   1. On load, the server-side template has already rendered the
 *      current state, including the absolute start/end timestamps
 *      as ISO-8601 strings in `data-starts` / `data-ends` attrs.
 *
 *   2. Every second, the timeRender pass recomputes the
 *      "remaining duration" string from those timestamps relative
 *      to the live wall clock — so the countdown looks smooth even
 *      though the server only refreshes the underlying data every
 *      cache-TTL seconds.
 *
 *   3. Every cache-TTL seconds the script polls /Embed/now-playing-
 *      data for fresh JSON and re-paints the DOM.  Browser HTTP
 *      cache means N parallel embeds share one round trip.
 *
 *   4. If the current item's end-time passes before the next poll
 *      would normally happen, a single extra poll is fired
 *      immediately to grab the new "current" item, so the widget
 *      flips to the next track / show with sub-second latency.
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-widget')) {
        return;
    }

    var widgetKind = body.getAttribute('data-widget'); // 'show' or 'track'
    var dataUrl    = body.getAttribute('data-data-url') || '/Embed/now-playing-data';
    var cacheTtlMs = parseInt(body.getAttribute('data-cache-ttl') || '60', 10) * 1000;

    // RASTATIME 2026-05-22 — empty-state labels.  Server-rendered
    // into data-attrs on first paint so the JS-side has a default
    // even before the first poll; the JSON payload then overrides
    // them on each refresh so a label change in the Widgets ->
    // Current Show/Track settings page shows up within one cache
    // TTL without a manual iframe reload.
    var labels = {
        noCurrent:  body.getAttribute('data-label-no-current')
                    || (widgetKind === 'show' ? 'No show on air' : 'No track playing'),
        noUpcoming: body.getAttribute('data-label-no-upcoming')
                    || (widgetKind === 'show' ? 'No upcoming show' : 'No upcoming track')
    };

    var failedPolls = 0;
    var MAX_FAILED_POLLS = 3;

    /*
     * Format a duration in milliseconds as "-MM:SS" or "-H:MM:SS".
     * Always prefixed with the minus sign to read as a countdown.
     * Returns an empty string when the source value is not finite.
     */
    function fmtRemaining(ms) {
        if (!isFinite(ms) || ms < 0) {
            return '00:00';
        }
        var totalSeconds = Math.floor(ms / 1000);
        var hours        = Math.floor(totalSeconds / 3600);
        var minutes      = Math.floor((totalSeconds % 3600) / 60);
        var seconds      = totalSeconds % 60;
        var pad = function (n) { return n < 10 ? '0' + n : String(n); };
        if (hours > 0) {
            return '-' + hours + ':' + pad(minutes) + ':' + pad(seconds);
        }
        return '-' + pad(minutes) + ':' + pad(seconds);
    }

    /*
     * Format a single ISO timestamp as "H:MM" — single-digit
     * hours render without the leading zero per operator
     * convention 2026-05-22 v10 (9:00, not 09:00); minutes
     * stay 2-digit so the colon-suffix is always present.
     * Falls back to the raw string if the input can't be parsed.
     */
    function fmtTimeOfDay(iso) {
        if (!iso) {
            return '';
        }
        var d = new Date(iso);
        if (isNaN(d.getTime())) {
            return iso;
        }
        var pad = function (n) { return n < 10 ? '0' + n : String(n); };
        return d.getHours() + ':' + pad(d.getMinutes());
    }

    /*
     * Format a start–end pair as "HH:MM - HH:MM".  If either bound
     * is missing the returned string degrades gracefully (we never
     * want to render an "undefined - 17:30" cell).
     */
    function fmtStartEnd(startIso, endIso) {
        var a = fmtTimeOfDay(startIso);
        var b = fmtTimeOfDay(endIso);
        if (!a && !b) {
            return '';
        }
        if (!a) {
            return '… - ' + b;
        }
        if (!b) {
            return a + ' - …';
        }
        return a + ' - ' + b;
    }

    /*
     * Pull the right pair of entries out of the server payload based
     * on the widget kind.  Returns { current, next } where each may
     * be null (no data) or { name|label, starts, ends }.
     */
    function pickEntries(payload) {
        if (widgetKind === 'show') {
            var c = payload.show && payload.show.current;
            var n = payload.show && payload.show.next;
            return {
                current: c ? { label: c.name, starts: c.starts, ends: c.ends } : null,
                next:    n ? { label: n.name, starts: n.starts, ends: n.ends } : null
            };
        }
        // track
        var ct = payload.track && payload.track.current;
        var nt = payload.track && payload.track.next;
        var labelFor = function (t) {
            if (!t) { return null; }
            var title  = (t.title  || '').trim();
            var artist = (t.artist || '').trim();
            if (!title && !artist) { return null; }
            if (!artist) { return title; }
            if (!title)  { return artist; }
            return artist + ' - ' + title;
        };
        // W4.1 — fileId/hasArtwork ride along so paint() can show a
        // cover.  Both are absent for show entries and for webstream /
        // line-in tracks, which is exactly when no cover must be built.
        return {
            current: ct ? {
                label: labelFor(ct), starts: ct.starts, ends: ct.ends,
                fileId: ct.fileId, hasArtwork: ct.hasArtwork
            } : null,
            next:    nt ? { label: labelFor(nt), starts: nt.starts, ends: nt.ends } : null
        };
    }

    /*
     * Repaint the DOM from a fresh entries object.
     */
    // W4.1 — cover settings + painter.  Never points the <img> at a
    // track without artwork: that endpoint answers 0-byte 200 and the
    // image would hang forever (neither load nor error fires).
    var artEnabled = body.getAttribute('data-art') === '1';
    var artUrlPrefix = body.getAttribute('data-art-url') || '';

    function paintCover(entry) {
        if (!artEnabled) { return; }
        var cover = document.querySelector('[data-np="cover"]');
        if (!cover) { return; }
        var img = cover.querySelector('img');
        if (!img) { return; }
        if (entry && entry.hasArtwork && entry.fileId) {
            var url = artUrlPrefix + encodeURIComponent(entry.fileId);
            if (img.getAttribute('src') !== url) { img.setAttribute('src', url); }
            cover.classList.add('np-cover-on');
        } else {
            cover.classList.remove('np-cover-on');
            img.removeAttribute('src');
        }
    }

    function paint(entries) {
        paintCover(entries.current);
        var currentName = document.querySelector('[data-np="current-name"]');
        var currentTime = document.querySelector('[data-np="current-time"]');
        var nextName    = document.querySelector('[data-np="next-name"]');
        var nextTime    = document.querySelector('[data-np="next-time"]');

        if (!currentName || !currentTime || !nextName || !nextTime) {
            return; // template mismatch — leave the DOM alone
        }

        var noCurrent = !entries.current || !entries.current.label;
        if (noCurrent) {
            body.classList.add('np-empty');
            currentName.textContent = labels.noCurrent;
            currentTime.removeAttribute('data-starts');
            currentTime.removeAttribute('data-ends');
            currentTime.textContent = '';
        } else {
            body.classList.remove('np-empty');
            currentName.textContent = entries.current.label;
            currentTime.setAttribute('data-starts', entries.current.starts || '');
            currentTime.setAttribute('data-ends',   entries.current.ends   || '');
        }

        var noNext = !entries.next || !entries.next.label;
        if (noNext) {
            nextName.textContent = labels.noUpcoming;
            nextTime.removeAttribute('data-starts');
            nextTime.removeAttribute('data-ends');
            nextTime.textContent = '';
        } else {
            nextName.textContent = entries.next.label;
            nextTime.setAttribute('data-starts', entries.next.starts || '');
            nextTime.setAttribute('data-ends',   entries.next.ends   || '');
        }
    }

    /*
     * Per-second countdown update.  Does not touch the names, only
     * the time cells, so a network blip never wipes the labels.
     */
    function tickCountdowns() {
        var now = Date.now();

        var currentTime = document.querySelector('[data-np="current-time"]');
        var nextTime    = document.querySelector('[data-np="next-time"]');

        if (currentTime) {
            var ends = currentTime.getAttribute('data-ends');
            if (ends) {
                var endMs = new Date(ends).getTime();
                currentTime.textContent = fmtRemaining(endMs - now);
                // If we've crossed the end-time, force an early poll
                // so the widget flips to the next item without
                // waiting out the cache TTL.
                if (endMs - now < 0 && endMs - now > -2000) {
                    pollOnce();
                }
            } else {
                currentTime.textContent = '';
            }
        }

        if (nextTime) {
            var nStart = nextTime.getAttribute('data-starts');
            var nEnd   = nextTime.getAttribute('data-ends');
            if (nStart || nEnd) {
                nextTime.textContent = fmtStartEnd(nStart, nEnd);
            } else {
                nextTime.textContent = '';
            }
        }
    }

    /*
     * Single poll round-trip to the JSON endpoint.  Updates stale
     * state and failed-poll counter so the CSS can dim the widget
     * when the backend is unreachable.
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
                // Pick up operator-configured empty labels from the
                // refresh payload so a settings change appears
                // within one poll without a manual iframe reload.
                if (payload.labels) {
                    if (widgetKind === 'show') {
                        labels.noCurrent  = payload.labels.noCurrentShow  || labels.noCurrent;
                        labels.noUpcoming = payload.labels.noUpcomingShow || labels.noUpcoming;
                    } else {
                        labels.noCurrent  = payload.labels.noCurrentTrack  || labels.noCurrent;
                        labels.noUpcoming = payload.labels.noUpcomingTrack || labels.noUpcoming;
                    }
                }
                paint(pickEntries(payload));
                // Repaint the time cells immediately so the user
                // doesn't see a 1-second flash of stale countdown.
                tickCountdowns();
            })
            .catch(function () {
                failedPolls++;
                if (failedPolls >= MAX_FAILED_POLLS) {
                    body.classList.add('np-stale');
                }
            });
    }

    // Boot: first countdown tick immediately so the widget isn't
    // empty for one second, then the regular cadence.
    tickCountdowns();
    setInterval(tickCountdowns, 1000);

    // Poll cadence matches the cache TTL so the browser cache
    // usually serves the request locally.  Add a small jitter
    // (±10 %) so massively-embedded widgets don't synchronise
    // their backend hits.
    var jitter = 0.9 + Math.random() * 0.2;
    setInterval(pollOnce, Math.max(10000, cacheTtlMs * jitter));
})();
