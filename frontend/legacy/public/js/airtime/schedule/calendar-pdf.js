/**
 * RASTATIME 2026-11-21 - the calendar view as a PDF.
 * ------------------------------------------------------------------
 * Operator request 2026-11-21: a button above the calendar grid, left of
 * Day / Week / Month (an export icon, schedule-fc6.css).  Decision (Go
 * 2026-11-21): built in the browser with pdfmake (already vendored for the
 * Playout History export), time + show, no month grid.  The menu item opens
 * a small dialog (second request the same day):
 *
 *   List      orientation (landscape / portrait) and the period: a day, the
 *             week around a date (station week start) or any period from -
 *             to (at most 92 days).  One page per day, rows
 *             "08:00 - 09:00  Show" with the show's colour, like the On Air
 *             Today / Weekly Schedule widgets.  A show that runs into the
 *             first day from the day before is listed first; a show across
 *             midnight is listed on the day it starts.  The shows come from
 *             the calendar's own feed (Schedule/event-feed) for that period,
 *             so it need not be on screen.
 *   Calendar  orientation; the day or week on screen as a time grid like
 *             the calendar and the Multi-View widget, coloured blocks in the
 *             show's colours.  Week: seven day columns of 24 h on one page.
 *             Day: the day in columns of six hours (landscape, four) or
 *             eight hours (portrait, three), so that the many short shows
 *             (news etc., under 10 min) still get a line of text.  Data:
 *             the shows the calendar has loaded for the view (FC6
 *             getEvents) - what the screen shows.
 *
 * A delete that is still counting down (undo-delete.js) is left out.  Times
 * are station time, as on screen (the feed sends naive station-local
 * timestamps).  pdfmake (~2 MB with its fonts) is only loaded on the first
 * export.  The last orientation per layout is remembered in this browser.
 */
(function (window, $) {
  "use strict";

  var A4_LONG = 841.89; // pt
  var A4_SHORT = 595.28;
  var MARGIN = 28;
  var TOP = 46; // below the page header
  var BOTTOM = 30; // above the page footer
  var MAX_DAYS = 92; // longest list period
  var DEFAULT_COLOR = "#6e6e6e";
  var HEX = /^#(?:[0-9a-f]{3}){1,2}$/i;
  var libsPromise = null;

  function t(text) {
    return $.i18n && $.i18n._ ? $.i18n._(text) : text;
  }

  function esc(text) {
    return $("<div/>").text(text).html();
  }

  function pref(key, value) {
    try {
      if (value === undefined) {
        return window.localStorage.getItem("rtCalendarPdf." + key);
      }
      window.localStorage.setItem("rtCalendarPdf." + key, value);
    } catch (e) {
      // private window / blocked storage: no memory, same defaults
    }
    return null;
  }

  // pdfmake + its fonts, once, in order (vfs_fonts needs pdfMake)
  function loadLibs() {
    if (window.pdfMake && window.pdfMake.vfs) {
      return Promise.resolve();
    }
    if (!libsPromise) {
      libsPromise = (window.rtPdfLibs || [])
        .reduce(function (chain, url) {
          return chain.then(function () {
            return new Promise(function (resolve, reject) {
              var s = document.createElement("script");
              s.src = url;
              s.onload = resolve;
              s.onerror = function () {
                reject(new Error("could not load " + url));
              };
              document.head.appendChild(s);
            });
          });
        }, Promise.resolve())
        .catch(function (err) {
          libsPromise = null; // a later click tries again
          throw err;
        });
    }
    return libsPromise;
  }

  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }

  function clock(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function isoDay(d) {
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function addDays(d, n) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  }

  function startOfDay(d) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function minuteOfDay(d) {
    return d.getHours() * 60 + d.getMinutes();
  }

  // "YYYY-MM-DD[ HH:MM[:SS]]" as a local (= station wall-clock) date
  function parseLocal(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(String(s || "").trim());
    if (!m) {
      return null;
    }
    var d = new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0));
    return d.getFullYear() === +m[1] && d.getMonth() === +m[2] - 1 && d.getDate() === +m[3] ? d : null;
  }

  function locale() {
    return typeof fc6Locale === "function" ? fc6Locale() : undefined;
  }

  function dayLabel(d, long) {
    var opts = long
      ? { weekday: "long", day: "numeric", month: "long", year: "numeric" }
      : { weekday: "short", day: "numeric", month: "numeric" };
    try {
      return d.toLocaleDateString(locale(), opts);
    } catch (e) {
      return isoDay(d);
    }
  }

  // the title of a period: "16 - 22 November 2026", via FC6 like the view title
  function rangeTitle(first, last) {
    if (isoDay(first) === isoDay(last)) {
      return dayLabel(first, true);
    }
    try {
      return window.FullCalendar.formatRange(first, last, {
        day: "numeric",
        month: "long",
        year: "numeric",
        locale: locale(),
        separator: " – ",
      });
    } catch (e) {
      return isoDay(first) + " – " + isoDay(last);
    }
  }

  function safeColor(color) {
    return HEX.test(color || "") ? color : DEFAULT_COLOR;
  }

  // black or white on the block colour, unless the show sets its text colour
  function textColorFor(ev) {
    if (HEX.test(ev.textColor || "")) {
      return ev.textColor;
    }
    var hex = safeColor(ev.color).slice(1);
    if (hex.length === 3) {
      hex = hex.replace(/(.)/g, "$1$1");
    }
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#000000" : "#ffffff";
  }

  // shorten to roughly the width a line can hold (Roboto averages a little
  // over half an em per character)
  function fit(text, width, fontSize) {
    var max = Math.max(1, Math.floor(width / (fontSize * 0.55)));
    text = String(text || "");
    return text.length > max ? text.slice(0, Math.max(1, max - 1)) + "…" : text;
  }

  function daysBetween(from, to) {
    var days = [];
    for (var d = startOfDay(from); d < to; d = addDays(d, 1)) {
      days.push(d);
    }
    return days;
  }

  function keep(ev, from, to) {
    var undo = window.rtUndoDelete;
    return (
      ev.start &&
      ev.start < to &&
      ev.end > from &&
      !(undo && typeof undo.isPending === "function" && undo.isPending(ev.id))
    );
  }

  function byTime(a, b) {
    return a.start - b.start || a.end - b.end;
  }

  // the shows the calendar has loaded for its view (the grid's data)
  function viewEvents(cal) {
    var from = cal.view.currentStart;
    var to = cal.view.currentEnd;
    return cal
      .getEvents()
      .map(function (ev) {
        return {
          id: ev.id,
          title: ev.title || "",
          start: ev.start,
          end: ev.end || ev.start,
          color: ev.backgroundColor,
          textColor: ev.textColor,
        };
      })
      .filter(function (ev) {
        return keep(ev, from, to);
      })
      .sort(byTime);
  }

  // the shows of any period, from the calendar's feed (the list's data)
  function fetchEvents(from, to) {
    return new Promise(function (resolve, reject) {
      $.post(baseUrl + "Schedule/event-feed", {
        format: "json",
        start: makeTimeStamp(from),
        end: makeTimeStamp(to),
        cachep: new Date().getTime(),
      })
        .done(function (json) {
          resolve(
            (json.events || [])
              .map(function (e) {
                var start = parseLocal(e.start);
                return {
                  id: e.id,
                  title: e.title || "",
                  start: start,
                  end: parseLocal(e.end) || start,
                  color: e.color,
                  textColor: e.textColor,
                };
              })
              .filter(function (ev) {
                return keep(ev, from, to);
              })
              .sort(byTime),
          );
        })
        .fail(function () {
          reject(new Error("Schedule/event-feed failed"));
        });
    });
  }

  function stationNow() {
    var now = new Date();
    if (typeof adjustDateToServerDate === "function" && typeof timezoneOffset !== "undefined") {
      return adjustDateToServerDate(now, timezoneOffset);
    }
    return now;
  }

  function page(orientation) {
    return orientation === "portrait" ? { w: A4_SHORT, h: A4_LONG } : { w: A4_LONG, h: A4_SHORT };
  }

  function frame(title, orientation) {
    var station = window.rtStationName || "";
    var created = stationNow();
    return {
      pageSize: "A4",
      pageOrientation: orientation === "portrait" ? "portrait" : "landscape",
      pageMargins: [MARGIN, TOP, MARGIN, BOTTOM],
      info: { title: (station ? station + " - " : "") + title, creator: "RASTATIME" },
      header: {
        margin: [MARGIN, 18, MARGIN, 0],
        fontSize: 12,
        text: station ? [{ text: station + "   ", bold: true }, title] : title,
      },
      footer: function (pageNo, pages) {
        return {
          margin: [MARGIN, 10, MARGIN, 0],
          fontSize: 7,
          color: "#777777",
          columns: [
            { text: isoDay(created) + " " + clock(created) },
            { text: pageNo + " / " + pages, alignment: "right" },
          ],
        };
      },
      defaultStyle: { fontSize: 9.5, color: "#222222" },
      content: [],
    };
  }

  // ---- List: one page per day -------------------------------------------
  // days: the dates of the period; events: its shows, sorted
  function listDocument(days, events, title, orientation) {
    var doc = frame(title, orientation);
    days.forEach(function (day, i) {
      var next = addDays(day, 1);
      var rows = events.filter(function (ev) {
        return ev.start < next && (i === 0 || ev.start >= day);
      });
      var heading = { text: dayLabel(day, true), fontSize: 12, bold: true, margin: [0, 0, 0, 6] };
      if (i > 0) {
        heading.pageBreak = "before";
      }
      doc.content.push(heading);
      if (!rows.length) {
        doc.content.push({ text: "–", color: "#777777" });
        return;
      }
      doc.content.push({
        table: {
          widths: [5, 72, "*"],
          body: rows.map(function (ev) {
            return [
              { text: "", fillColor: safeColor(ev.color) },
              { text: clock(ev.start) + " – " + clock(ev.end) },
              { text: ev.title },
            ];
          }),
        },
        layout: {
          hLineWidth: function (n, node) {
            return n === 0 || n === node.table.body.length ? 0 : 0.3;
          },
          vLineWidth: function () {
            return 0;
          },
          hLineColor: function () {
            return "#cccccc";
          },
          paddingLeft: function (n) {
            return n === 0 ? 0 : 6;
          },
          paddingRight: function () {
            return 4;
          },
          paddingTop: function () {
            return 2.5;
          },
          paddingBottom: function () {
            return 2.5;
          },
        },
      });
    });
    return doc;
  }

  // ---- Calendar: a time grid on one page --------------------------------
  // columns: [{ day, from, to, label }] in minutes of the day; all columns
  // span the same number of minutes.  ownAxis: hour labels in every column
  // (the day view's columns) instead of one axis on the left.
  function gridDocument(cal, orientation) {
    var size = page(orientation);
    var portrait = orientation === "portrait";
    var days = daysBetween(cal.view.currentStart, cal.view.currentEnd);
    var events = viewEvents(cal);
    var week = days.length > 1;
    var columns = [];
    if (week) {
      days.forEach(function (day) {
        columns.push({ day: day, from: 0, to: 1440, label: dayLabel(day, false) });
      });
    } else {
      var hours = portrait ? 8 : 6;
      for (var q = 0; q < 24 / hours; q++) {
        columns.push({
          day: days[0],
          from: q * hours * 60,
          to: (q + 1) * hours * 60,
          label: pad(q * hours) + ":00 – " + pad((q + 1) * hours) + ":00",
        });
      }
    }
    var ownAxis = !week;
    var doc = frame(week ? cal.view.title : dayLabel(days[0], true), orientation);
    var axisW = 26;
    var headH = 15;
    var top = TOP + headH;
    var bottom = size.h - BOTTOM;
    var left = MARGIN + (ownAxis ? 0 : axisW);
    var slot = (size.w - MARGIN - left) / columns.length; // column incl. own axis
    var span = columns[0].to - columns[0].from;
    var perMin = (bottom - top) / span;
    var fs = week ? (portrait ? 6 : 6.5) : 7.5;
    var lh = fs * 1.2;
    var shapes = [];
    var texts = [];

    function text(str, x, y, opts) {
      return $.extend({ text: str, absolutePosition: { x: x, y: y }, noWrap: true }, opts || {});
    }

    columns.forEach(function (col, c) {
      var x0 = left + c * slot + (ownAxis ? axisW : 0);
      var w = slot - (ownAxis ? axisW : 0);
      if (c % 2 === 1) {
        shapes.push({ type: "rect", x: x0, y: top, w: w, h: bottom - top, color: "#f3f3f3" });
      }
      texts.push(text(fit(col.label, w - 4, 8), x0 + 2, top - headH + 3, { fontSize: 8, bold: true }));
      for (var m = col.from; m <= col.to; m += 60) {
        var y = top + (m - col.from) * perMin;
        shapes.push({
          type: "line",
          x1: x0,
          y1: y,
          x2: x0 + w,
          y2: y,
          lineWidth: m % 360 === 0 ? 0.6 : 0.25,
          lineColor: "#bbbbbb",
        });
        if (m < col.to && (ownAxis || c === 0)) {
          texts.push(
            text(pad(m / 60) + ":00", (ownAxis ? x0 - axisW : MARGIN) + 1, y + 1, {
              fontSize: 6.5,
              color: "#666666",
            }),
          );
        }
      }
      shapes.push({ type: "line", x1: x0, y1: top, x2: x0, y2: bottom, lineWidth: 0.3, lineColor: "#bbbbbb" });
      shapes.push({ type: "line", x1: x0 + w, y1: top, x2: x0 + w, y2: bottom, lineWidth: 0.3, lineColor: "#bbbbbb" });

      var dayStart = col.day;
      var dayEnd = addDays(col.day, 1);
      events.forEach(function (ev) {
        if (!(ev.start < dayEnd && ev.end > dayStart)) {
          return;
        }
        // wall-clock minutes (a day with a clock change still maps 0..1440)
        var s = ev.start < dayStart ? 0 : minuteOfDay(ev.start);
        var e = ev.end >= dayEnd ? 1440 : minuteOfDay(ev.end);
        s = Math.max(s, col.from);
        e = Math.min(e, col.to);
        if (e <= s) {
          return;
        }
        var bx = x0 + 1;
        var bw = w - 2;
        var by = top + (s - col.from) * perMin;
        var bh = (e - s) * perMin;
        var fg = textColorFor(ev);
        shapes.push({
          type: "rect",
          x: bx,
          y: by + 0.3,
          w: bw,
          h: Math.max(bh - 0.6, 0.6),
          r: 1.2,
          color: safeColor(ev.color),
          lineColor: "#ffffff",
          lineWidth: 0.4,
        });
        // the label carries the show's own times, also on the piece of a
        // show that continues from the previous column or day
        var times = clock(ev.start) + " – " + clock(ev.end);
        if (bh >= 2 * lh + 2) {
          texts.push(text(fit(times, bw - 4, fs), bx + 2, by + 1.5, { fontSize: fs, color: fg }));
          texts.push(text(fit(ev.title, bw - 4, fs), bx + 2, by + 1.5 + lh, { fontSize: fs, color: fg, bold: true }));
        } else if (bh >= lh + 0.5) {
          texts.push(
            text(fit(clock(ev.start) + "  " + ev.title, bw - 4, fs), bx + 2, by + (bh - lh) / 2 + 0.6, {
              fontSize: fs,
              color: fg,
            }),
          );
        }
      });
    });

    doc.content.push({ canvas: shapes, absolutePosition: { x: 0, y: 0 } });
    doc.content = doc.content.concat(texts);
    return doc;
  }

  function fileName(kind, first, last) {
    var a = isoDay(first);
    var b = isoDay(last);
    return "calendar-" + kind + "-" + a + (b !== a ? "_" + b : "") + ".pdf";
  }

  function failed(err) {
    if (window.console) {
      console.error("calendar PDF:", err);
    }
    alert(t("The PDF could not be created."));
  }

  // opts: { orientation, from, to } - from / to (exclusive) for the list
  function buildPdf(kind, opts) {
    var cal = window.scheduleFc6;
    opts = opts || {};
    var orientation = opts.orientation === "portrait" ? "portrait" : "landscape";
    if (kind === "grid" && cal.view.type === "dayGridMonth") {
      // no month grid (operator 2026-11-21): the month as a list
      kind = "list";
      opts = $.extend({ from: cal.view.currentStart, to: cal.view.currentEnd }, opts);
    }
    if (kind === "grid") {
      var gridDays = daysBetween(cal.view.currentStart, cal.view.currentEnd);
      return loadLibs().then(function () {
        return {
          doc: gridDocument(cal, orientation),
          name: fileName("grid", gridDays[0], gridDays[gridDays.length - 1]),
        };
      });
    }
    var from = opts.from;
    var to = opts.to;
    var days = daysBetween(from, to);
    var last = days[days.length - 1];
    return Promise.all([loadLibs(), fetchEvents(from, to)]).then(function (res) {
      return {
        doc: listDocument(days, res[1], rangeTitle(from, last), orientation),
        name: fileName("list", from, last),
      };
    });
  }

  function exportPdf(kind, opts) {
    return buildPdf(kind, opts).then(function (pdf) {
      window.pdfMake.createPdf(pdf.doc).download(pdf.name);
    });
  }

  // ---- the dialog ---------------------------------------------------------
  function datepickerOptions() {
    var o = {
      dateFormat: "yy-mm-dd",
      firstDay: typeof calendarPref !== "undefined" ? parseInt(calendarPref.weekStart, 10) || 0 : 0,
    };
    if (typeof i18n_months !== "undefined") {
      o.monthNames = i18n_months;
    }
    if (typeof i18n_days_short !== "undefined") {
      o.dayNamesMin = i18n_days_short;
    }
    return o;
  }

  function weekStartDay() {
    return typeof calendarPref !== "undefined" ? parseInt(calendarPref.weekStart, 10) || 0 : 0;
  }

  // the list period the dialog asks for, or an error text
  function readPeriod($d) {
    var range = $d.find("input[name=rt-pdf-range]:checked").val();
    if (range === "custom") {
      var from = parseLocal($d.find(".rt-pdf-from").val());
      var last = parseLocal($d.find(".rt-pdf-to").val());
      if (!from || !last || last < from) {
        return { error: t("Choose a valid period.") };
      }
      if (daysBetween(from, addDays(last, 1)).length > MAX_DAYS) {
        return { error: t("The period may be at most 92 days.") };
      }
      return { range: range, from: startOfDay(from), to: addDays(last, 1) };
    }
    var date = parseLocal($d.find(".rt-pdf-date").val());
    if (!date) {
      return { error: t("Choose a valid date.") };
    }
    if (range === "week") {
      var start = addDays(date, -((date.getDay() - weekStartDay() + 7) % 7));
      return { range: range, from: start, to: addDays(start, 7) };
    }
    return { range: "day", from: startOfDay(date), to: addDays(date, 1) };
  }

  function openDialog(kind) {
    var cal = window.scheduleFc6;
    if (!cal) {
      return;
    }
    var isList = kind === "list";
    var view = cal.view;
    var orientation = pref(kind + ".orientation") === "portrait" ? "portrait" : "landscape";
    var range =
      view.type === "timeGridDay" ? "day" : view.type === "timeGridWeek" ? "week" : "custom";
    var viewLast = addDays(view.currentEnd, -1);

    function radio(name, value, label, checked) {
      return (
        '<label class="rt-pdf-option"><input type="radio" name="' +
        name +
        '" value="' +
        value +
        '"' +
        (checked ? " checked" : "") +
        "> " +
        esc(label) +
        "</label>"
      );
    }

    var html =
      '<div class="rt-pdf-dialog">' +
      '<div class="rt-pdf-row"><span class="rt-pdf-label">' +
      esc(t("Orientation")) +
      "</span>" +
      radio("rt-pdf-orient", "landscape", t("Landscape"), orientation === "landscape") +
      radio("rt-pdf-orient", "portrait", t("Portrait"), orientation === "portrait") +
      "</div>";
    if (isList) {
      html +=
        '<div class="rt-pdf-row"><span class="rt-pdf-label">' +
        esc(t("Period")) +
        "</span>" +
        radio("rt-pdf-range", "day", t("Day"), range === "day") +
        radio("rt-pdf-range", "week", t("Week"), range === "week") +
        radio("rt-pdf-range", "custom", t("Custom period"), range === "custom") +
        "</div>" +
        '<div class="rt-pdf-row rt-pdf-when rt-pdf-when-date"><span class="rt-pdf-label">' +
        esc(t("Date")) +
        '</span><input type="text" class="input_text rt-pdf-date" autocomplete="off"></div>' +
        '<div class="rt-pdf-row rt-pdf-when rt-pdf-when-custom"><span class="rt-pdf-label">' +
        esc(t("From")) +
        '</span><input type="text" class="input_text rt-pdf-from" autocomplete="off">' +
        '<span class="rt-pdf-to-label">' +
        esc(t("To")) +
        '</span><input type="text" class="input_text rt-pdf-to" autocomplete="off"></div>';
    }
    html += '<div class="rt-pdf-error"></div></div>';

    var $d = $(html);

    function syncRange() {
      var custom = $d.find("input[name=rt-pdf-range]:checked").val() === "custom";
      $d.find(".rt-pdf-when-date").toggle(!custom);
      $d.find(".rt-pdf-when-custom").toggle(custom);
      $d.find(".rt-pdf-error").text("");
    }

    function submit() {
      var opts = { orientation: $d.find("input[name=rt-pdf-orient]:checked").val() };
      if (isList) {
        var period = readPeriod($d);
        if (period.error) {
          $d.find(".rt-pdf-error").text(period.error);
          return;
        }
        opts.from = period.from;
        opts.to = period.to;
      }
      pref(kind + ".orientation", opts.orientation);
      $d.dialog("close");
      exportPdf(kind, opts).catch(failed);
    }

    $d.dialog({
      modal: true,
      width: isList ? 470 : 330,
      resizable: false,
      title: t(isList ? "List" : "Calendar") + " (PDF)",
      classes: { "ui-dialog": "schedule-tracks-dialog rt-pdf-ui" },
      open: function () {
        if (typeof markScheduleDialogOverlay === "function") {
          markScheduleDialogOverlay.apply(this, arguments);
        }
      },
      close: function () {
        $d.find(".hasDatepicker").datepicker("destroy");
        $d.dialog("destroy").remove();
      },
      buttons: [
        { text: t("Export"), class: "btn", click: submit },
        {
          text: t("Cancel"),
          class: "btn",
          click: function () {
            $d.dialog("close");
          },
        },
      ],
    });

    if (isList) {
      var dp = datepickerOptions();
      $d.find(".rt-pdf-date").val(isoDay(cal.getDate())).datepicker(dp);
      $d.find(".rt-pdf-from").val(isoDay(view.currentStart)).datepicker(dp);
      $d.find(".rt-pdf-to").val(isoDay(viewLast)).datepicker(dp);
      $d.on("change", "input[name=rt-pdf-range]", syncRange);
      $d.on("input change", "input.input_text", function () {
        $d.find(".rt-pdf-error").text("");
      });
      $d.on("keydown", "input.input_text", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          submit();
        }
      });
      syncRange();
    }
  }

  // the toolbar button opens a small menu: List / Calendar (no Calendar in
  // the month view).  Delegated, so it survives FC6 rebuilding the toolbar.
  $(function () {
    if (!$.contextMenu) {
      return;
    }
    $.contextMenu({
      selector: ".fc-rtPdf-button",
      trigger: "left",
      className: "calendar-context-menu",
      build: function () {
        var cal = window.scheduleFc6;
        var items = { list: { name: t("List") } };
        if (!cal || cal.view.type !== "dayGridMonth") {
          items.grid = { name: t("Calendar") };
        }
        return {
          items: items,
          callback: function (key) {
            openDialog(key);
          },
        };
      },
    });
  });

  // for tests in the browser console
  window.rtCalendarPdf = {
    openDialog: openDialog,
    buildPdf: buildPdf,
    exportPdf: exportPdf,
    listDocument: listDocument,
    gridDocument: gridDocument,
    fetchEvents: fetchEvents,
    loadLibs: loadLibs,
  };
})(window, jQuery);
