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
    var emptyLabel  = body.getAttribute('data-label-empty') || 'No shows scheduled';

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
     * Format a start/end time-of-day pair as "HH:MM – HH:MM"
     * in the visitor's locale.
     */
    function fmtTimeRange(start, end) {
        try {
            var opts = { hour: '2-digit', minute: '2-digit' };
            return start.toLocaleTimeString(undefined, opts)
                + ' – ' + end.toLocaleTimeString(undefined, opts);
        } catch (e) {
            return pad2(start.getHours()) + ':' + pad2(start.getMinutes())
                + ' – ' + pad2(end.getHours()) + ':' + pad2(end.getMinutes());
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
     * Mark the currently-airing event so the CSS can ring it.
     * Recomputed after every fetch — fetch happens on view
     * change / navigation, which is the same trigger we want
     * for the "is this still on air?" recomputation.
     * --------------------------------------------------------
     */
    function markCurrentEvent(calendar) {
        if (!calendar) { return; }
        var now = Date.now();
        calendar.getEvents().forEach(function (ev) {
            var startMs = ev.start ? ev.start.getTime() : 0;
            var endMs   = ev.end   ? ev.end.getTime()   : 0;
            var isCurrent = (startMs <= now && endMs > now);
            // FullCalendar's setExtendedProp triggers a re-render
            // of just that event, which lets us toggle the
            // .np-mv-event-current class via the
            // eventClassNames callback below.
            ev.setExtendedProp('isCurrent', isCurrent);
        });
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
        allDaySlot: false,
        expandRows: true,
        height: '100%',
        stickyHeaderDates: true,
        firstDay: 1,                             // Monday — matches station convention
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
         * after every event re-render.
         */
        eventClassNames: function (arg) {
            return arg.event.extendedProps.isCurrent
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
         * After each fetch, mark the current event + scroll to
         * the now-line (only on first load, or after a Today
         * click).  Tracked with a one-shot flag so subsequent
         * navigations don't re-snap the view.
         */
        eventsSet: function () {
            markCurrentEvent(calendar);
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
