/*
 * RASTATIME 2026-05-22 — Multi-View Schedule widget runtime.
 *
 * Mounts FullCalendar 6 (vendored at /js/libs/fullcalendar/) on
 * the #np-mv-calendar element, with operator-switchable Day /
 * 2-Day / Week views, a custom header bar, and a click-to-open
 * modal for show details.
 *
 * Data source:
 *   /Embed/multi-view-schedule-data?from=YYYY-MM-DD&to=YYYY-MM-DD&timezone=...
 *   returns { success: true, events: [...] } in FullCalendar's
 *   documented event shape.  Server caches 5 min by default
 *   (overridable via the iframe's ?cache=N URL parameter).
 *
 * Inspired by the operator's existing radio-calendar prototype
 * (see https://example.org/radio-calendar/), reworked to
 * source from RASTATIME's cc_show_instances + cc_show instead
 * of an Outlook calendar bridge.
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-multi-view-schedule')) {
        return;
    }
    if (typeof FullCalendar === 'undefined') {
        // FullCalendar didn't load — surface a clear error in the
        // calendar area so an operator notices instead of seeing
        // a silent empty pane.
        var el = document.getElementById('np-mv-calendar');
        if (el) {
            el.textContent = 'FullCalendar library failed to load.';
            el.style.padding = '20px';
            el.style.color = 'var(--np-fg-muted)';
            el.style.fontStyle = 'italic';
        }
        return;
    }

    var defaultView = body.getAttribute('data-default-view') || 'day';
    var timezone    = body.getAttribute('data-timezone') || 'UTC';
    var locale      = body.getAttribute('data-locale') || 'en';
    var clockMode   = body.getAttribute('data-clock')  || '24';   // '12' | '24' | 'auto'
    var emptyLabel  = body.getAttribute('data-label-empty') || 'No shows scheduled';
    // RASTATIME 2026-10-25 - Settings -> General -> Week Starts On (0 = Sunday)
    var firstDay    = parseInt(body.getAttribute('data-first-day'), 10);
    if (isNaN(firstDay) || firstDay < 0 || firstDay > 6) {
        firstDay = 1;
    }

    /*
     * Build a FullCalendar time-format OBJECT that the
     * slotLabelFormat / eventTimeFormat options can consume.
     * Returns `undefined` for "auto" so FullCalendar falls back
     * to the locale default.
     *
     * v12 lesson learned: the v11 attempt at cmdline-format
     * strings ('H:mm' / 'h:mm a') broke FullCalendar's init
     * and made all events invisible.  Reverted to the object
     * form which FullCalendar 6 reliably accepts.  Padding-zero
     * on hours is handled separately via slotLabelContent /
     * the eventContent callback below (those run AFTER the
     * Intl format and let us rewrite the text deterministically).
     */
    function clockFormat(includeMinutes) {
        if (clockMode === 'auto') { return undefined; }
        var hour12 = (clockMode === '12');
        var fmt = {
            hour: 'numeric',
            hour12: hour12,
            meridiem: hour12 ? 'short' : false
        };
        if (includeMinutes) {
            fmt.minute = '2-digit';
        }
        return fmt;
    }

    /*
     * Deterministic time formatter for slot labels + event chips,
     * applied via the slotLabelContent / eventContent callbacks.
     * Bypasses Intl entirely so we get exactly "9", "9:00",
     * "9:00 AM" regardless of locale.  Operator request
     * 2026-05-22 v12: Intl with hour:'numeric' silently pads
     * to 2-digit in some locale + meridiem combinations.
     */
    function formatHourMinute(d, includeMinutes) {
        if (!d) { return ''; }
        var h = d.getHours();
        var m = d.getMinutes();
        if (clockMode === '12' || (clockMode === 'auto' && shouldUse12hForLocale())) {
            var ampm = h >= 12 ? 'PM' : 'AM';
            var h12 = h % 12 || 12;
            return h12 + (includeMinutes ? (':' + pad2(m)) : '') + ' ' + ampm;
        }
        // 24h (clockMode='24', or 'auto' with a 24h locale)
        return h + (includeMinutes ? (':' + pad2(m)) : '');
    }

    /*
     * Detect whether the visitor's locale would render time as
     * AM/PM by default.  Used only when clockMode === 'auto'.
     * Falls back to false (24h) if Intl is unavailable.
     */
    function shouldUse12hForLocale() {
        try {
            var resolved = new Intl.DateTimeFormat(locale, { hour: 'numeric' })
                .resolvedOptions();
            return resolved.hour12 === true;
        } catch (e) {
            return false;
        }
    }

    /*
     * Map the operator-friendly view names ('day', '2day',
     * 'week') to the FullCalendar view names.  'day' and 'week'
     * are built-in; '2day' is a custom view we register inline.
     */
    var VIEW_MAP = {
        day:   'timeGridDay',
        '2day': 'timeGridTwoDay',
        week:  'timeGridWeek'
    };

    /*
     * DOM references — cached so the per-tick navigation /
     * activation handlers don't re-query the document.
     */
    var el = {
        calendarMount: document.getElementById('np-mv-calendar'),
        range:         document.querySelector('[data-np="range"]'),
        prev:          document.querySelector('[data-np="prev"]'),
        next:          document.querySelector('[data-np="next"]'),
        today:         document.querySelector('[data-np="today"]'),
        viewButtons:   document.querySelectorAll('.np-mv-view'),
        modal:         document.querySelector('[data-np="modal"]'),
        modalOverlay:  document.querySelector('[data-np="modal-overlay"]'),
        modalTitle:    document.querySelector('[data-np="modal-title"]'),
        modalTime:     document.querySelector('[data-np="modal-time"]'),
        modalDesc:     document.querySelector('[data-np="modal-description"]'),
        modalLink:     document.querySelector('[data-np="modal-link"]'),
        modalClose:    document.querySelector('[data-np="modal-close"]')
    };
    if (!el.calendarMount) { return; }

    /*
     * --------------------------------------------------------
     * Helpers
     * --------------------------------------------------------
     */

    function pad2(n) { return n < 10 ? '0' + n : String(n); }

    /*
     * Format a Date as a YYYY-MM-DD string in *local* time
     * (matches the way the controller parses ?from / ?to).
     */
    function fmtLocalDate(d) {
        return d.getFullYear()
            + '-' + pad2(d.getMonth() + 1)
            + '-' + pad2(d.getDate());
    }

    /*
     * Format a start/end time-of-day pair for the modal header.
     * Honours the ?clock= operator setting so the modal matches
     * the rest of the widget — operator's 24h widget shouldn't
     * suddenly switch to AM/PM in the modal popover.
     */
    function fmtTimeRange(start, end) {
        // Manual format for 24h: guarantees single-digit hours
        // without leading zero ("9:00" not "09:00"), with
        // 2-digit minutes ("9:05" not "9:5").  Operator-requested
        // convention 2026-05-22 v11.  Intl.toLocaleTimeString
        // with hour:'numeric' would mostly do the same but is
        // less deterministic across browsers + locale combos.
        function fmt24(d) {
            return d.getHours() + ':' + pad2(d.getMinutes());
        }
        function fmt12(d) {
            var h = d.getHours();
            var ampm = h >= 12 ? 'PM' : 'AM';
            var h12 = h % 12 || 12;
            return h12 + ':' + pad2(d.getMinutes()) + ' ' + ampm;
        }
        if (clockMode === '12') {
            return fmt12(start) + ' – ' + fmt12(end);
        }
        if (clockMode === '24') {
            return fmt24(start) + ' – ' + fmt24(end);
        }
        // 'auto' — fall back to locale default
        try {
            var opts = { hour: 'numeric', minute: '2-digit' };
            return start.toLocaleTimeString(undefined, opts)
                + ' – ' + end.toLocaleTimeString(undefined, opts);
        } catch (e) {
            return fmt24(start) + ' – ' + fmt24(end);
        }
    }

    /*
     * Format the header range label based on the active view.
     * Day → "Fri 22 May 2026"
     * 2-Day → "Fri 22 – Sat 23 May 2026"
     * Week → "Mon 19 – Sun 25 May 2026"
     */
    function fmtRange(view) {
        if (!view) { return ''; }
        var start = view.currentStart;
        // FullCalendar's `currentEnd` is exclusive; subtract 1 ms
        // to get the last day inside the range for display.
        var endIncl = new Date(view.currentEnd.getTime() - 1);

        try {
            var dowMon = { weekday: 'short', day: 'numeric', month: 'short' };
            var dowMonYr = { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' };
            if (start.toDateString() === endIncl.toDateString()) {
                return start.toLocaleDateString(undefined, dowMonYr);
            }
            if (start.getFullYear() === endIncl.getFullYear()) {
                return start.toLocaleDateString(undefined, dowMon)
                    + ' – '
                    + endIncl.toLocaleDateString(undefined, dowMonYr);
            }
            return start.toLocaleDateString(undefined, dowMonYr)
                + ' – '
                + endIncl.toLocaleDateString(undefined, dowMonYr);
        } catch (e) {
            return fmtLocalDate(start) + ' – ' + fmtLocalDate(endIncl);
        }
    }

    /*
     * --------------------------------------------------------
     * Modal
     * --------------------------------------------------------
     */

    function showModal(event) {
        if (!el.modal) { return; }
        var title = event.title || '';
        var start = event.start;
        var end   = event.end;
        var desc  = (event.extendedProps && event.extendedProps.description) || '';
        var url   = (event.extendedProps && event.extendedProps.url) || '';

        el.modalTitle.textContent = title;
        el.modalTime.textContent  = (start && end) ? fmtTimeRange(start, end) : '';
        el.modalDesc.textContent  = desc || '';

        if (url) {
            body.classList.remove('np-mv-no-link');
            el.modalLink.href = url;
        } else {
            body.classList.add('np-mv-no-link');
            el.modalLink.removeAttribute('href');
        }

        el.modal.classList.add('np-mv-modal-visible');
        el.modalOverlay.classList.add('np-mv-modal-visible');
    }

    function hideModal() {
        if (!el.modal) { return; }
        el.modal.classList.remove('np-mv-modal-visible');
        el.modalOverlay.classList.remove('np-mv-modal-visible');
    }

    if (el.modalClose)   { el.modalClose.addEventListener('click', hideModal); }
    if (el.modalOverlay) { el.modalOverlay.addEventListener('click', hideModal); }
    document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') { hideModal(); }
    });

    /*
     * --------------------------------------------------------
     * Is this event currently on air?  Evaluated client-side
     * from Date.now() so we don't have to mutate the event
     * objects (which used to trigger an eventsSet → re-render
     * → eventsSet infinite loop that froze the browser).
     *
     * Re-evaluated on every render (which FullCalendar does on
     * view change, navigation, and refetch).  Doesn't track
     * the clock on a per-second basis — if the operator leaves
     * the iframe open for a full hour, the highlight stays on
     * the show that was current at last paint.  Acceptable
     * trade-off: the alternative would mean a setInterval
     * that periodically dirties the calendar, which is heavier
     * than the value of an exact live highlight.
     * --------------------------------------------------------
     */
    function isCurrentEvent(ev) {
        if (!ev || !ev.start || !ev.end) { return false; }
        var now = Date.now();
        return ev.start.getTime() <= now && ev.end.getTime() > now;
    }

    /*
     * --------------------------------------------------------
     * Auto-scroll to the now-indicator line.  FullCalendar
     * renders the line itself when `nowIndicator: true`; we
     * just centre it in the calendar's scroll viewport.
     * --------------------------------------------------------
     */
    function scrollToNow() {
        var nowLine = el.calendarMount.querySelector('.fc-timegrid-now-indicator-line');
        if (!nowLine) {
            // Fallback: scroll based on the current local hour.
            var hours = new Date().getHours();
            // Each hour is ~2 * 28 px = 56 px at the default
            // 15-min slot height; centre 1.5 hours above the
            // current hour for context.
            el.calendarMount.scrollTop = Math.max(0, (hours - 1.5) * 56);
            return;
        }
        // Compute the now-line's offset relative to the scroll
        // container manually so we don't accidentally scroll
        // the embedding iframe via scrollIntoView's ancestor
        // walk.
        var lineRect = nowLine.getBoundingClientRect();
        var mountRect = el.calendarMount.getBoundingClientRect();
        var offsetWithinMount = (lineRect.top - mountRect.top) + el.calendarMount.scrollTop;
        el.calendarMount.scrollTop = Math.max(
            0,
            offsetWithinMount - (el.calendarMount.clientHeight / 2)
        );
    }

    /*
     * --------------------------------------------------------
     * Initialise the calendar.
     * --------------------------------------------------------
     */

    var calendar = new FullCalendar.Calendar(el.calendarMount, {
        initialView: VIEW_MAP[defaultView] || 'timeGridDay',
        locale: locale,
        headerToolbar: false,                    // we render our own header
        nowIndicator: true,
        slotMinTime: '00:00',
        slotMaxTime: '24:00',
        slotDuration: '00:15:00',
        slotLabelInterval: '01:00',
        // Operator request 2026-05-22 v10: don't visually
        // overlap events.  FullCalendar's default (true) packs
        // back-to-back events into half-width columns when their
        // boundaries kiss; setting false renders each event in
        // the full column width unless they genuinely overlap
        // in time (rare in a radio schedule).
        slotEventOverlap: false,
        // Operator-controlled clock format (?clock=12|24|auto).
        // `undefined` lets FullCalendar pick the locale default
        // (e.g. "5 PM" for en, "17:00" for de); explicit object
        // overrides regardless of locale.
        slotLabelFormat:  clockFormat(false),   // hour only on the axis
        eventTimeFormat:  clockFormat(true),    // hour + minutes in event chips

        // Override the text Intl gives us for slot labels with a
        // deterministic "no-leading-zero" formatter — Intl's
        // hour:'numeric' silently pads to 2-digit in some locale
        // + meridiem combinations, which the operator's German
        // locale exposed.  This runs AFTER slotLabelFormat so we
        // get the final say on what shows up on the hour axis.
        slotLabelContent: function (arg) {
            return { html: formatHourMinute(arg.date, false) };
        },

        // Same deterministic-formatter trick for the time chip
        // inside each event.  We rebuild the event chip's inner
        // HTML so the time + title both live in there without
        // the default 2-digit padding.
        eventContent: function (arg) {
            var timeText = formatHourMinute(arg.event.start, true);
            var endText  = arg.event.end
                ? formatHourMinute(arg.event.end, true)
                : '';
            var title    = arg.event.title || '';
            var time     = endText ? (timeText + ' - ' + endText) : timeText;
            // Mark up time + title in separate spans so the
            // existing FullCalendar CSS variables can colour
            // them.  Title escaping: setting via textContent
            // would be safer, but here we render a small wrapper
            // HTML and pass the title via a textContent step.
            var titleHtml = document.createElement('div');
            titleHtml.className = 'fc-event-title fc-sticky';
            titleHtml.textContent = title;
            var timeDiv  = document.createElement('div');
            timeDiv.className = 'fc-event-time';
            timeDiv.textContent = time;
            var wrapper  = document.createElement('div');
            wrapper.className = 'fc-event-main-frame';
            wrapper.appendChild(timeDiv);
            wrapper.appendChild(titleHtml);
            return { domNodes: [wrapper] };
        },
        allDaySlot: false,
        expandRows: true,
        height: '100%',
        stickyHeaderDates: true,
        firstDay: firstDay,                      // Settings -> General -> Week Starts On
        views: {
            timeGridTwoDay: {
                type: 'timeGrid',
                duration: { days: 2 }
            }
        },

        /*
         * Lazy-load events for whatever range the active view
         * needs.  FullCalendar calls this when the view is
         * created, when the operator navigates ◀ / ▶, and
         * when they switch view types.  Server-side cache
         * absorbs the polling cost.
         */
        events: function (info, success, failure) {
            var from = fmtLocalDate(info.start);
            // FullCalendar's `info.end` is exclusive — pass it
            // straight through; the controller also treats `to`
            // as exclusive.
            var to = fmtLocalDate(info.end);
            var url = '/Embed/multi-view-schedule-data'
                + '?from=' + encodeURIComponent(from)
                + '&to='   + encodeURIComponent(to)
                + '&timezone=' + encodeURIComponent(timezone);
            fetch(url, { credentials: 'omit', cache: 'default' })
                .then(function (r) {
                    if (!r.ok) { throw new Error('HTTP ' + r.status); }
                    return r.json();
                })
                .then(function (payload) {
                    if (!payload.success) {
                        throw new Error(payload.error || 'unknown');
                    }
                    success(payload.events || []);
                })
                .catch(function (err) {
                    failure(err);
                });
        },

        /*
         * Tag the currently-airing event with a CSS class so
         * the surrounding stylesheet can outline it.  Re-runs
         * after every event re-render.  Evaluated directly
         * against Date.now() — see isCurrentEvent comment for
         * why we don't mutate the event with setExtendedProp.
         */
        eventClassNames: function (arg) {
            return isCurrentEvent(arg.event)
                ? ['np-mv-event-current']
                : [];
        },

        /*
         * Always open the modal — even when the show has a URL,
         * the operator wants to see the description first
         * (operator request: "Modal mit Beschreibung + URL-
         * Button im Modal").  The modal's link button carries
         * the URL when present.
         */
        eventClick: function (info) {
            info.jsEvent.preventDefault();
            showModal(info.event);
        },

        /*
         * After each fetch, optionally scroll to the now-line
         * (only on first load, or after a Today click).
         * Tracked with a one-shot flag so subsequent navigations
         * don't re-snap the view.  Note: we deliberately do NOT
         * mutate any event here — that would re-trigger
         * eventsSet via the FullCalendar re-render and loop the
         * browser into the "page unresponsive" warning that
         * shipped with v1 of this widget.
         */
        eventsSet: function () {
            if (pendingScrollToNow) {
                pendingScrollToNow = false;
                // Defer until the now-indicator line has been
                // painted (FullCalendar inserts it after the
                // events).
                requestAnimationFrame(scrollToNow);
            }
            updateHeader();
        }
    });

    /*
     * --------------------------------------------------------
     * Header chrome — date range label + active-view button.
     * --------------------------------------------------------
     */

    function updateHeader() {
        var view = calendar.view;
        if (el.range) {
            el.range.textContent = fmtRange(view);
        }
        // Reverse-lookup the active view in VIEW_MAP so the
        // button toggle matches what the calendar is showing.
        var activeKey = null;
        Object.keys(VIEW_MAP).forEach(function (k) {
            if (VIEW_MAP[k] === view.type) { activeKey = k; }
        });
        el.viewButtons.forEach(function (btn) {
            btn.classList.toggle('np-mv-view-active',
                btn.getAttribute('data-view') === activeKey);
        });
    }

    /*
     * Pending-scroll flag: set whenever the operator clicks
     * "Today" (or on first paint).  Picked up by the next
     * `eventsSet` callback so the scroll lands after the
     * now-indicator-line has been rendered.
     */
    var pendingScrollToNow = true;

    if (el.prev) {
        el.prev.addEventListener('click', function () {
            calendar.prev();
        });
    }
    if (el.next) {
        el.next.addEventListener('click', function () {
            calendar.next();
        });
    }
    if (el.today) {
        el.today.addEventListener('click', function () {
            calendar.today();
            pendingScrollToNow = true;
        });
    }
    el.viewButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var v = btn.getAttribute('data-view');
            if (VIEW_MAP[v]) {
                calendar.changeView(VIEW_MAP[v]);
                pendingScrollToNow = true;
            }
        });
    });

    /*
     * --------------------------------------------------------
     * Boot
     * --------------------------------------------------------
     */
    calendar.render();
    updateHeader();
})();
