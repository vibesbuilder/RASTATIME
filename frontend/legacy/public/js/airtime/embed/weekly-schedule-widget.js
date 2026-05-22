/*
 * RASTATIME 2026-05-22 — Weekly Schedule Widget v2 runtime.
 *
 * Vanilla JS replacement for the upstream jQuery 1.8.3 + Handlebars
 * widget.  No external dependencies, no jQuery — runs in any
 * browser that supports fetch + Intl.DateTimeFormat (Chrome 42+,
 * Firefox 39+, Safari 10.1+, Edge 14+).
 *
 * Behaviour:
 *
 *   1. The server pre-renders a `<script type="application/json">`
 *      block carrying the full week payload from
 *      WidgetHelper::getWeekInfoV2(weekOffset).  On boot, JS parses
 *      that block, builds the 7-day tab strip + the per-day show
 *      panels, and pre-selects today's tab (or the first day when
 *      the offset puts the visible window into the past / future).
 *
 *   2. ◀ / ▶ buttons update the `?week_offset` URL parameter
 *      in-place via history.pushState and trigger a full iframe
 *      reload.  Cheap, and the browser cache deduplicates back-
 *      and-forth navigation.
 *
 *   3. The tab strip swaps the active panel without touching the
 *      tab block — no flicker, no network round-trip.  Today's
 *      day-of-month is decorated with a pill ring so the operator
 *      can scan the strip quickly.
 *
 *   4. Show names get wrapped in an <a target="_blank"> when the
 *      payload carries a non-empty url; otherwise they render as
 *      plain text.  CSS class on the body controls the link
 *      style (?link=plain vs ?link=underline).
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-weekly-schedule')) {
        return;
    }

    var weekOffset    = parseInt(body.getAttribute('data-week-offset') || '0', 10);
    var weekOffsetMin = parseInt(body.getAttribute('data-week-offset-min') || '-2', 10);
    var weekOffsetMax = parseInt(body.getAttribute('data-week-offset-max') || '4', 10);
    var currentDom    = parseInt(body.getAttribute('data-current-dom') || '0', 10);
    var timezone      = body.getAttribute('data-timezone') || '';
    var emptyLabel    = body.getAttribute('data-label-empty') || 'No shows scheduled on this day';

    var dataScript = document.getElementById('np-ws-data');
    if (!dataScript) {
        return;
    }
    var payload = null;
    try {
        payload = JSON.parse(dataScript.textContent || '{}');
    } catch (e) {
        return;
    }
    if (!payload || !payload.weekDays) {
        return;
    }

    /*
     * Helpers ------------------------------------------------------
     */
    function pad2(n) { return n < 10 ? '0' + n : String(n); }

    /*
     * Translate a JS Date into the visitor's locale "HH:MM" string.
     * Used to render the per-show start / end columns.
     */
    function fmtTimeOfDay(d) {
        return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
    }

    /*
     * Format a day-of-month + month-short label like "21 May".
     * Used by the header range label and the day tabs.
     */
    function fmtDayMonth(d) {
        try {
            return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
        } catch (e) {
            var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                          'Jul','Aug','Sep','Oct','Nov','Dec'];
            return d.getDate() + ' ' + MONTHS[d.getMonth()];
        }
    }

    /*
     * Build a single "Mon" weekday abbreviation in the visitor's
     * locale.  Falls back to a fixed English list on Intl-failure.
     */
    function fmtWeekdayShort(d) {
        try {
            return d.toLocaleDateString(undefined, { weekday: 'short' });
        } catch (e) {
            var WEEKDAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
            return WEEKDAYS[d.getDay()];
        }
    }

    /*
     * Parse the upstream "Y-n-j" day key (e.g. "2026-5-21") into a
     * JS Date set to noon local — noon avoids DST edge cases that
     * could push the date to the previous / next day.
     */
    function parseDayKey(key) {
        var m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(key);
        if (!m) { return null; }
        return new Date(parseInt(m[1], 10),
                        parseInt(m[2], 10) - 1,
                        parseInt(m[3], 10), 12, 0, 0);
    }

    /*
     * Pre-process the payload: each show gets bucketed into the
     * day it starts in (in the visitor's local timezone), so the
     * panel rendering doesn't have to scan the full show list per
     * day.  Matches the convention the upstream Handlebars
     * template already used.
     */
    function bucketShows(weekDays, shows) {
        // First pass: ensure every weekday has a shows[] array.
        Object.keys(weekDays).forEach(function (k) {
            if (!Array.isArray(weekDays[k].shows)) {
                weekDays[k].shows = [];
            }
        });

        (shows || []).forEach(function (s) {
            var startDate = new Date(s.starts_timestamp * 1000);
            var endDate   = new Date(s.ends_timestamp * 1000);
            var key = startDate.getFullYear()
                + '-' + (startDate.getMonth() + 1)
                + '-' + startDate.getDate();
            if (weekDays[key]) {
                weekDays[key].shows.push({
                    starts: startDate,
                    ends:   endDate,
                    name:   s.name || '',
                    url:    s.url || ''
                });
            }
        });

        // Sort each day's shows by start time so the panel is
        // chronological even if the upstream payload wasn't.
        Object.keys(weekDays).forEach(function (k) {
            weekDays[k].shows.sort(function (a, b) {
                return a.starts.getTime() - b.starts.getTime();
            });
        });
    }

    /*
     * Render the header range label ("21 May – 27 May 2026") from
     * the first and last day keys.  Year-boundary windows show the
     * year twice ("28 Dec 2025 – 3 Jan 2026") so the operator
     * always has the full context.
     */
    function renderRange(orderedKeys) {
        var rangeEl = document.querySelector('[data-np="range"]');
        if (!rangeEl) { return; }
        if (!orderedKeys.length) {
            rangeEl.textContent = '';
            return;
        }
        var first = parseDayKey(orderedKeys[0]);
        var last  = parseDayKey(orderedKeys[orderedKeys.length - 1]);
        if (!first || !last) {
            rangeEl.textContent = '';
            return;
        }
        var firstYear = first.getFullYear();
        var lastYear  = last.getFullYear();
        var firstLabel = fmtDayMonth(first);
        var lastLabel  = fmtDayMonth(last);
        if (firstYear === lastYear) {
            rangeEl.textContent = firstLabel + ' – ' + lastLabel + ' ' + lastYear;
        } else {
            rangeEl.textContent = firstLabel + ' ' + firstYear
                + ' – ' + lastLabel + ' ' + lastYear;
        }
    }

    /*
     * Render the 7-tab strip and the 7 day-panels.  Tabs get the
     * .np-ws-tab-today class for whichever tab matches today's
     * day-of-month (only relevant when weekOffset === 0).  Active
     * tab is the first one by default, unless weekOffset === 0 in
     * which case today is pre-selected.
     */
    function render(orderedKeys, weekDays) {
        var tabsEl    = document.querySelector('[data-np="tabs"]');
        var contentEl = document.querySelector('[data-np="content"]');
        if (!tabsEl || !contentEl) { return; }

        // Clear any previous render (relevant for future polling
        // refreshes — the current implementation does full iframe
        // reload on ◀ / ▶, but a future refresh path could swap
        // the inner DOM only).
        tabsEl.innerHTML = '';
        contentEl.innerHTML = '';

        var todayKeyMatched = false;
        orderedKeys.forEach(function (key, idx) {
            var day = weekDays[key];
            var d = parseDayKey(key);
            if (!d || !day) { return; }

            // Tab
            var li = document.createElement('li');
            li.className = 'np-ws-tab';
            li.setAttribute('data-day-idx', String(idx));

            var dowSpan = document.createElement('span');
            dowSpan.className = 'np-ws-tab-dow';
            dowSpan.textContent = fmtWeekdayShort(d);
            li.appendChild(dowSpan);

            var domSpan = document.createElement('span');
            domSpan.className = 'np-ws-tab-dom';
            domSpan.textContent = String(d.getDate());
            li.appendChild(domSpan);

            // "Today" decoration only when this tab's day matches
            // the station-local today AND we're on weekOffset 0.
            if (weekOffset === 0 && d.getDate() === currentDom) {
                li.classList.add('np-ws-tab-today');
                todayKeyMatched = true;
            }
            tabsEl.appendChild(li);

            // Day panel
            var panel = document.createElement('div');
            panel.className = 'np-ws-day';
            panel.setAttribute('data-day-idx', String(idx));

            if (!day.shows || day.shows.length === 0) {
                var emptyEl = document.createElement('div');
                emptyEl.className = 'np-ws-empty';
                emptyEl.textContent = emptyLabel;
                panel.appendChild(emptyEl);
            } else {
                day.shows.forEach(function (s) {
                    var row = document.createElement('div');
                    row.className = 'np-ws-row';

                    var timeSpan = document.createElement('span');
                    timeSpan.className = 'np-ws-row-time';
                    timeSpan.textContent = fmtTimeOfDay(s.starts)
                        + ' - ' + fmtTimeOfDay(s.ends);
                    row.appendChild(timeSpan);

                    var nameSpan = document.createElement('span');
                    nameSpan.className = 'np-ws-row-name np-name';
                    if (s.url) {
                        var a = document.createElement('a');
                        a.href = s.url;
                        a.target = '_blank';
                        a.rel = 'noopener noreferrer';
                        a.textContent = s.name;
                        nameSpan.appendChild(a);
                    } else {
                        nameSpan.textContent = s.name;
                    }
                    row.appendChild(nameSpan);

                    panel.appendChild(row);
                });
            }
            contentEl.appendChild(panel);
        });

        // Activate the right tab + panel by default:
        // - weekOffset === 0 AND today's tab is present → today
        // - otherwise → first tab
        var activeIdx = 0;
        if (todayKeyMatched) {
            // Find the today-tab index.
            var todays = tabsEl.querySelectorAll('.np-ws-tab-today');
            if (todays.length > 0) {
                activeIdx = parseInt(todays[0].getAttribute('data-day-idx') || '0', 10);
            }
        }
        activate(activeIdx);

        // Wire tab clicks to activate().
        tabsEl.addEventListener('click', function (ev) {
            var t = ev.target;
            while (t && t !== tabsEl && !t.classList.contains('np-ws-tab')) {
                t = t.parentNode;
            }
            if (!t || t === tabsEl) { return; }
            var idx = parseInt(t.getAttribute('data-day-idx') || '0', 10);
            activate(idx);
        });
    }

    function activate(idx) {
        var tabs   = document.querySelectorAll('.np-ws-tab');
        var panels = document.querySelectorAll('.np-ws-day');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].classList.toggle('np-ws-tab-active',
                String(idx) === tabs[i].getAttribute('data-day-idx'));
        }
        for (var j = 0; j < panels.length; j++) {
            panels[j].classList.toggle('np-ws-day-active',
                String(idx) === panels[j].getAttribute('data-day-idx'));
        }
    }

    /*
     * Wire ◀ / ▶ buttons to navigate weeks.  Clamp at the server-
     * supplied min / max (operator-set: -2 / +4 by default).
     * Buttons that would push the offset past the limit get
     * disabled (visual + click-blocking) so the user sees they've
     * hit the boundary instead of clicking into a no-op.
     */
    function wireNavigation() {
        var prev = document.querySelector('[data-np="prev-week"]');
        var next = document.querySelector('[data-np="next-week"]');

        // Reflect the boundary state into the disabled attribute
        // — picks up CSS opacity + cursor: not-allowed for free.
        if (prev) { prev.disabled = (weekOffset <= weekOffsetMin); }
        if (next) { next.disabled = (weekOffset >= weekOffsetMax); }

        function navigate(deltaWeeks) {
            var target = Math.max(weekOffsetMin,
                          Math.min(weekOffsetMax, weekOffset + deltaWeeks));
            if (target === weekOffset) { return; }
            var url = new URL(window.location.href);
            if (target === 0) {
                url.searchParams.delete('week_offset');
            } else {
                url.searchParams.set('week_offset', String(target));
            }
            window.location.href = url.toString();
        }
        if (prev) {
            prev.addEventListener('click', function () {
                if (!prev.disabled) { navigate(-1); }
            });
        }
        if (next) {
            next.addEventListener('click', function () {
                if (!next.disabled) { navigate(+1); }
            });
        }
    }

    /*
     * Boot ---------------------------------------------------------
     */
    bucketShows(payload.weekDays, payload.shows);
    var orderedKeys = Object.keys(payload.weekDays);
    renderRange(orderedKeys);
    render(orderedKeys, payload.weekDays);
    wireNavigation();
})();
