/*
 * RASTATIME 2026-05-22 — Track History widget runtime.
 *
 * Behaviour:
 *   1. On boot: fetch page 1 for today (or whatever ?date= says).
 *   2. Date-picker change → reset page to 1, re-fetch.
 *   3. Pagesize dropdown change → reset page to 1, re-fetch.
 *   4. Today button → snap date back to today, reset, re-fetch.
 *   5. Load-more button → page++, append to existing list.
 *   6. Track-row click → open modal with full metadata.
 *
 * Hard cap of 10 pages × 100 pagesize = 1000 rows total, but
 * each fetch is one page (10-100 rows) so the wire payload
 * stays modest.  Server clamps independently.
 */

(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('np-track-history')) {
        return;
    }

    var minDate     = body.getAttribute('data-min-date');
    var maxDate     = body.getAttribute('data-max-date');
    var timezone    = body.getAttribute('data-timezone') || 'UTC';
    var emptyLabel  = body.getAttribute('data-label-empty') || 'No tracks played on this day';

    var currentDay      = body.getAttribute('data-day-local');
    var currentPagesize = parseInt(body.getAttribute('data-pagesize') || '10', 10);
    var currentPage     = 1;
    var isLoading       = false;

    var el = {
        dateInput:    document.querySelector('[data-np="date"]'),
        todayBtn:     document.querySelector('[data-np="today"]'),
        pagesize:     document.querySelector('[data-np="pagesize"]'),
        list:         document.querySelector('[data-np="list"]'),
        loadmore:     document.querySelector('[data-np="loadmore"]'),
        status:       document.querySelector('[data-np="status"]'),
        modal:        document.querySelector('[data-np="modal"]'),
        modalOverlay: document.querySelector('[data-np="modal-overlay"]'),
        modalTitle:   document.querySelector('[data-np="modal-title"]'),
        modalArtist:  document.querySelector('[data-np="modal-artist"]'),
        modalTime:    document.querySelector('[data-np="modal-time"]'),
        modalShow:    document.querySelector('[data-np="modal-show"]'),
        modalLink:    document.querySelector('[data-np="modal-link"]'),
        modalClose:   document.querySelector('[data-np="modal-close"]')
    };

    /* ----------------------------------------------------------
     * Helpers
     * ---------------------------------------------------------- */

    function pad2(n) { return n < 10 ? '0' + n : String(n); }

    /*
     * Format a JS Date as "H:MM" — operator-requested
     * convention 2026-05-22 v10: no leading zero on the hour,
     * 2-digit minute.
     */
    function fmtTimeOfDay(d) {
        if (!d) { return ''; }
        return d.getHours() + ':' + pad2(d.getMinutes());
    }

    function fmtTimeRange(start, end) {
        var s = fmtTimeOfDay(start);
        var e = end ? fmtTimeOfDay(end) : '';
        return e ? (s + ' - ' + e) : s;
    }

    /*
     * Compose "Artist - Title", "Title" (artist empty), or
     * "Artist" (title empty) for the row display.  Returns
     * empty string only when both are blank — the SQL filter
     * already drops those.
     */
    function trackLabel(track) {
        var t = (track.title || '').trim();
        var a = (track.artist || '').trim();
        if (a && t) { return a + ' - ' + t; }
        if (t)      { return t; }
        return a;
    }

    /* ----------------------------------------------------------
     * Modal
     * ---------------------------------------------------------- */

    function showModal(track) {
        if (!el.modal) { return; }
        var start = track.starts ? new Date(track.starts) : null;
        var end   = track.ends   ? new Date(track.ends)   : null;

        el.modalTitle.textContent  = track.title  || '(no title)';
        el.modalArtist.textContent = track.artist || '';
        el.modalTime.textContent   = start ? fmtTimeRange(start, end) : '';

        var showName = (track.show && track.show.name) || '';
        var showUrl  = (track.show && track.show.url)  || '';
        if (showName) {
            el.modalShow.textContent = showName;
            el.modalShow.style.display = '';
        } else {
            el.modalShow.style.display = 'none';
        }

        if (showUrl) {
            body.classList.remove('np-th-no-link');
            el.modalLink.href = showUrl;
        } else {
            body.classList.add('np-th-no-link');
            el.modalLink.removeAttribute('href');
        }

        el.modal.classList.add('np-th-modal-visible');
        el.modalOverlay.classList.add('np-th-modal-visible');
    }

    function hideModal() {
        if (!el.modal) { return; }
        el.modal.classList.remove('np-th-modal-visible');
        el.modalOverlay.classList.remove('np-th-modal-visible');
    }

    if (el.modalClose)   { el.modalClose.addEventListener('click', hideModal); }
    if (el.modalOverlay) { el.modalOverlay.addEventListener('click', hideModal); }
    document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') { hideModal(); }
    });

    /* ----------------------------------------------------------
     * List rendering
     * ---------------------------------------------------------- */

    function renderRows(tracks, append) {
        if (!el.list) { return; }
        if (!append) {
            el.list.innerHTML = '';
        }
        if (!tracks.length && !append) {
            var li = document.createElement('li');
            li.className = 'np-th-empty';
            li.textContent = emptyLabel;
            el.list.appendChild(li);
            return;
        }
        tracks.forEach(function (track) {
            var li = document.createElement('li');
            li.className = 'np-th-row';

            var timeSpan = document.createElement('span');
            timeSpan.className = 'np-th-row-time';
            var startDate = track.starts ? new Date(track.starts) : null;
            timeSpan.textContent = startDate ? fmtTimeOfDay(startDate) : '';
            li.appendChild(timeSpan);

            var titleSpan = document.createElement('span');
            titleSpan.className = 'np-th-row-title';
            titleSpan.textContent = trackLabel(track);
            li.appendChild(titleSpan);

            li.addEventListener('click', function () {
                showModal(track);
            });

            el.list.appendChild(li);
        });
    }

    /* ----------------------------------------------------------
     * Fetch
     * ---------------------------------------------------------- */

    function fetchPage(page, append) {
        if (isLoading) { return; }
        isLoading = true;
        if (el.status) { el.status.textContent = '…'; }
        if (el.loadmore) { el.loadmore.disabled = true; }

        var url = '/Embed/track-history-data'
            + '?date='     + encodeURIComponent(currentDay)
            + '&pagesize=' + currentPagesize
            + '&page='     + page
            + '&timezone=' + encodeURIComponent(timezone);

        fetch(url, { credentials: 'omit', cache: 'default' })
            .then(function (r) {
                if (!r.ok) { throw new Error('HTTP ' + r.status); }
                return r.json();
            })
            .then(function (payload) {
                isLoading = false;
                if (el.status) { el.status.textContent = ''; }
                if (el.loadmore) { el.loadmore.disabled = false; }

                if (payload.labels && payload.labels.noTrackHistory) {
                    emptyLabel = payload.labels.noTrackHistory;
                }

                renderRows(payload.tracks || [], append);

                if (payload.hasMore) {
                    el.loadmore.style.display = '';
                } else {
                    el.loadmore.style.display = 'none';
                }
            })
            .catch(function () {
                isLoading = false;
                if (el.status) {
                    el.status.textContent = '— error loading tracks';
                }
                if (el.loadmore) { el.loadmore.disabled = false; }
            });
    }

    /* ----------------------------------------------------------
     * Event wiring
     * ---------------------------------------------------------- */

    if (el.dateInput) {
        el.dateInput.addEventListener('change', function () {
            var v = el.dateInput.value;
            if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) { return; }
            // Soft-clamp to [minDate, maxDate].
            if (v < minDate) { v = minDate; el.dateInput.value = v; }
            if (v > maxDate) { v = maxDate; el.dateInput.value = v; }
            currentDay  = v;
            currentPage = 1;
            fetchPage(1, false);
        });
    }

    if (el.todayBtn) {
        el.todayBtn.addEventListener('click', function () {
            if (el.dateInput) { el.dateInput.value = maxDate; }
            currentDay  = maxDate;
            currentPage = 1;
            fetchPage(1, false);
        });
    }

    if (el.pagesize) {
        el.pagesize.addEventListener('change', function () {
            var v = parseInt(el.pagesize.value, 10);
            if ([10, 20, 50, 100].indexOf(v) === -1) { v = 10; }
            currentPagesize = v;
            currentPage = 1;
            fetchPage(1, false);
        });
    }

    if (el.loadmore) {
        el.loadmore.addEventListener('click', function () {
            if (currentPage >= 10) { return; }   // hard cap
            currentPage += 1;
            fetchPage(currentPage, true);
        });
    }

    /* ----------------------------------------------------------
     * Boot
     * ---------------------------------------------------------- */
    fetchPage(1, false);
})();
