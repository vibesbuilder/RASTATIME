/**
 * RASTATIME 2026-06-01 (JS-modernization stage 2): FullCalendar 6 Schedule.
 * ------------------------------------------------------------------
 * Replaces the forked FullCalendar 1.5 (js/fullcalendar/) on the Schedule page
 * with the vendored FC6 (js/libs/fullcalendar/) — the same lib the embed
 * Multi-View widget already uses.  FC6 is vanilla (no jQuery) -> removes a
 * jQuery dependency (the stage-2 goal).
 *
 * Phase a (read-only): calendar shell + event source + station-time display +
 * the three views.  Interactions (create / drag / resize / context menu) and the
 * rich event rendering (fill bar + status icons) are the next steps.
 *
 * Enabled with ?fc6=1; FC1.5 stays the default fallback until FC6 is fully
 * verified.  createFullCalendar() in schedule.js branches here.
 *
 * Timezone: the server returns event start/end as naive station-local
 * timestamps ("YYYY-MM-DD HH:MM:SS"); FC6 (timeZone 'local') renders the
 * wall-clock numbers verbatim -> station time in every browser.  FC6's `now`
 * option is set to station time so the now-line and "today" land correctly,
 * replacing the old serverTimezoneOffset hand-patch in the forked lib.
 */
var scheduleFc6 = null;

// View-name mapping: the stored preference + FC1.5 use agendaDay/agendaWeek/
// month; FC6 uses timeGridDay/timeGridWeek/dayGridMonth.
var FC6_VIEW_FROM_LEGACY = {
  agendaDay: "timeGridDay",
  agendaWeek: "timeGridWeek",
  month: "dayGridMonth",
};
var FC6_VIEW_TO_LEGACY = {
  timeGridDay: "agendaDay",
  timeGridWeek: "agendaWeek",
  dayGridMonth: "month",
};

function fc6Locale() {
  var l =
    window.LOCALE ||
    (window.$ && $("html").attr("lang")) ||
    (navigator.language || "en");
  return String(l).toLowerCase().split("-")[0].split("_")[0];
}

function fc6Isoify(s) {
  // server sends naive station-local "YYYY-MM-DD HH:MM:SS"; FC6 wants ISO.
  return typeof s === "string" ? s.replace(" ", "T") : s;
}

function getScheduleFc6Events(info, success, failure) {
  var startDate = makeTimeStamp(info.start);
  var endDate = makeTimeStamp(info.end);
  var url = baseUrl + "Schedule/event-feed";
  var d = new Date();
  $.post(url, {
    format: "json",
    start: startDate,
    end: endDate,
    cachep: d.getTime(),
  })
    .done(function (json) {
      var events = (json.events || []).map(function (e) {
        // FC6 reads id/start/end/title; every other field lands in
        // event.extendedProps automatically.
        var ev = $.extend({}, e);
        ev.start = fc6Isoify(e.start);
        ev.end = fc6Isoify(e.end);
        return ev;
      });
      success(events);
    })
    .fail(function () {
      failure(new Error("Schedule/event-feed failed"));
    });
}

function buildScheduleFc6(data) {
  var el = document.getElementById("schedule_calendar");
  if (!el || !window.FullCalendar) {
    return;
  }
  var legacyView = getTimeScalePreference(data); // agendaDay/agendaWeek/month
  var slotMin = getTimeIntervalPreference(data); // minutes
  var offset = parseInt(data.calendarInit.timezoneOffset, 10);

  if (scheduleFc6) {
    scheduleFc6.destroy();
  }

  scheduleFc6 = new FullCalendar.Calendar(el, {
    initialView: FC6_VIEW_FROM_LEGACY[legacyView] || "timeGridDay",
    locale: fc6Locale(),
    firstDay: parseInt(data.calendarInit.weekStartDay, 10) || 0,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridDay,timeGridWeek,dayGridMonth",
    },
    buttonText: {
      today: $.i18n._("Today"),
      month: $.i18n._("Month"),
      week: $.i18n._("Week"),
      day: $.i18n._("Day"),
    },
    nowIndicator: true,
    // station time for "now" / "today" (replaces the FC1.5 serverTimezoneOffset
    // hand-patch); the server feeds naive station-local event times.
    now: function () {
      return adjustDateToServerDate(new Date(), offset);
    },
    allDaySlot: false,
    slotDuration: "00:" + pad(slotMin, 2) + ":00",
    slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    expandRows: true,
    height: $(window).height() - 200 - 35,
    editable: false, // Phase a: read-only
    events: getScheduleFc6Events,

    // basic event chip: time + title (the fill bar + status icons come next)
    eventContent: function (arg) {
      var wrap = document.createElement("div");
      wrap.className = "fc-event-main-frame";
      var time = document.createElement("div");
      time.className = "fc-event-time";
      time.textContent = arg.timeText || "";
      var title = document.createElement("div");
      title.className = "fc-event-title fc-sticky";
      title.textContent = arg.event.title || "";
      wrap.appendChild(time);
      wrap.appendChild(title);
      return { domNodes: [wrap] };
    },

    // tag the DOM so the existing CSS hooks + later phases can find the instance
    eventDidMount: function (arg) {
      arg.el.classList.add("fc-show-instance-" + arg.event.id);
      if (arg.event.extendedProps.showId != null) {
        arg.el.setAttribute("data-show-id", arg.event.extendedProps.showId);
      }
    },

    // persist the view preference (legacy name) when the view changes
    datesSet: function (arg) {
      var legacy = FC6_VIEW_TO_LEGACY[arg.view.type];
      if (
        legacy &&
        typeof calendarPref !== "undefined" &&
        calendarPref &&
        calendarPref.timeScale !== legacy
      ) {
        calendarPref.timeScale = legacy;
        $.post(baseUrl + "Schedule/set-time-scale/format/json", {
          timeScale: legacy,
        });
      }
    },
  });

  scheduleFc6.render();
}

// Enable via ?fc6=1 — FC1.5 stays the default fallback until FC6 is verified.
window.SCHEDULE_USE_FC6 = /[?&]fc6=1/.test(window.location.search);
