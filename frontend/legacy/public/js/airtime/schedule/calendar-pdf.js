/**
 * RASTATIME 2026-11-21 - the calendar view as a PDF.
 * ------------------------------------------------------------------
 * Operator request 2026-11-21: a button above the calendar grid, left of
 * Day / Week / Month, that exports the current view.  Decision (Go
 * 2026-11-21): built in the browser with pdfmake (already vendored for the
 * Playout History export), time + show, A4 landscape, no month grid.
 *
 *   List      every view: one page per day, rows "08:00 - 09:00  Show" with
 *             the show's colour, like the On Air Today / Weekly Schedule
 *             widgets.  A show that runs into the first day from the day
 *             before is listed first; a show across midnight is listed on
 *             the day it starts.
 *   Calendar  day and week view: a time grid like the calendar and the
 *             Multi-View widget, coloured blocks in the show's colours.
 *             Week: seven day columns of 24 h on one page.  Day: the day in
 *             four columns of six hours, so that the many short shows
 *             (news etc., under 10 min) still get a line of text.
 *
 * The data are the shows the calendar has loaded for the view (FC6
 * getEvents) - what the screen shows; a delete that is still counting down
 * (undo-delete.js) is left out.  Times are station time, as on screen (the
 * feed sends naive station-local timestamps).  pdfmake (~2 MB with its
 * fonts) is only loaded on the first export.
 */
(function (window, $) {
  "use strict";

  var PAGE_W = 841.89; // A4 landscape, pt
  var PAGE_H = 595.28;
  var MARGIN = 28;
  var TOP = 46; // below the page header
  var BOTTOM = 30; // above the page footer
  var DEFAULT_COLOR = "#6e6e6e";
  var HEX = /^#(?:[0-9a-f]{3}){1,2}$/i;
  var libsPromise = null;

  function t(text) {
    return $.i18n && $.i18n._ ? $.i18n._(text) : text;
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

  function minuteOfDay(d) {
    return d.getHours() * 60 + d.getMinutes();
  }

  function dayLabel(d, long) {
    var locale = typeof fc6Locale === "function" ? fc6Locale() : undefined;
    var opts = long
      ? { weekday: "long", day: "numeric", month: "long", year: "numeric" }
      : { weekday: "short", day: "numeric", month: "numeric" };
    try {
      return d.toLocaleDateString(locale, opts);
    } catch (e) {
      return isoDay(d);
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

  // the days of the view (its current range, not the padding days)
  function viewDays(view) {
    var days = [];
    var d = new Date(
      view.currentStart.getFullYear(),
      view.currentStart.getMonth(),
      view.currentStart.getDate(),
    );
    while (d < view.currentEnd) {
      days.push(d);
      d = addDays(d, 1);
    }
    return days;
  }

  function viewEvents(cal) {
    var from = cal.view.currentStart;
    var to = cal.view.currentEnd;
    var undo = window.rtUndoDelete;
    return cal
      .getEvents()
      .filter(function (ev) {
        var end = ev.end || ev.start;
        return (
          ev.start < to &&
          end > from &&
          !(undo && typeof undo.isPending === "function" && undo.isPending(ev.id))
        );
      })
      .map(function (ev) {
        return {
          title: ev.title || "",
          start: ev.start,
          end: ev.end || ev.start,
          color: ev.backgroundColor,
          textColor: ev.textColor,
        };
      })
      .sort(function (a, b) {
        return a.start - b.start || a.end - b.end;
      });
  }

  function stationNow() {
    var now = new Date();
    if (typeof adjustDateToServerDate === "function" && typeof timezoneOffset !== "undefined") {
      return adjustDateToServerDate(now, timezoneOffset);
    }
    return now;
  }

  function frame(title) {
    var station = window.rtStationName || "";
    var created = stationNow();
    return {
      pageSize: "A4",
      pageOrientation: "landscape",
      pageMargins: [MARGIN, TOP, MARGIN, BOTTOM],
      info: { title: (station ? station + " - " : "") + title, creator: "RASTATIME" },
      header: {
        margin: [MARGIN, 18, MARGIN, 0],
        fontSize: 12,
        text: station ? [{ text: station + "   ", bold: true }, title] : title,
      },
      footer: function (page, pages) {
        return {
          margin: [MARGIN, 10, MARGIN, 0],
          fontSize: 7,
          color: "#777777",
          columns: [
            { text: isoDay(created) + " " + clock(created) },
            { text: page + " / " + pages, alignment: "right" },
          ],
        };
      },
      defaultStyle: { fontSize: 9.5, color: "#222222" },
      content: [],
    };
  }

  // ---- List: one page per day -------------------------------------------
  function listDocument(cal) {
    var days = viewDays(cal.view);
    var events = viewEvents(cal);
    var doc = frame(cal.view.title);
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
          hLineWidth: function (i, node) {
            return i === 0 || i === node.table.body.length ? 0 : 0.3;
          },
          vLineWidth: function () {
            return 0;
          },
          hLineColor: function () {
            return "#cccccc";
          },
          paddingLeft: function (i) {
            return i === 0 ? 0 : 6;
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
  // (the day view's six-hour columns) instead of one axis on the left.
  function gridDocument(cal) {
    var days = viewDays(cal.view);
    var events = viewEvents(cal);
    var week = days.length > 1;
    var columns = [];
    if (week) {
      days.forEach(function (day) {
        columns.push({ day: day, from: 0, to: 1440, label: dayLabel(day, false) });
      });
    } else {
      for (var q = 0; q < 4; q++) {
        columns.push({
          day: days[0],
          from: q * 360,
          to: (q + 1) * 360,
          label: pad(q * 6) + ":00 – " + pad((q + 1) * 6) + ":00",
        });
      }
    }
    var ownAxis = !week;
    var doc = frame(week ? cal.view.title : dayLabel(days[0], true));
    var axisW = 26;
    var headH = 15;
    var top = TOP + headH;
    var bottom = PAGE_H - BOTTOM;
    var left = MARGIN + (ownAxis ? 0 : axisW);
    var slot = (PAGE_W - MARGIN - left) / columns.length; // column incl. own axis
    var span = columns[0].to - columns[0].from;
    var perMin = (bottom - top) / span;
    var fs = week ? 6.5 : 7.5;
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

  function fileName(cal, kind) {
    var days = viewDays(cal.view);
    var first = isoDay(days[0]);
    var last = isoDay(days[days.length - 1]);
    return "calendar-" + kind + "-" + first + (last !== first ? "_" + last : "") + ".pdf";
  }

  function exportPdf(kind) {
    var cal = window.scheduleFc6;
    if (!cal) {
      return;
    }
    if (kind === "grid" && cal.view.type === "dayGridMonth") {
      kind = "list"; // no month grid (operator 2026-11-21)
    }
    loadLibs()
      .then(function () {
        var doc = kind === "grid" ? gridDocument(cal) : listDocument(cal);
        window.pdfMake.createPdf(doc).download(fileName(cal, kind));
      })
      .catch(function (err) {
        if (window.console) {
          console.error("calendar PDF:", err);
        }
        alert(t("The PDF could not be created."));
      });
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
            exportPdf(key);
          },
        };
      },
    });
  });

  // for tests in the browser console
  window.rtCalendarPdf = {
    exportPdf: exportPdf,
    listDocument: listDocument,
    gridDocument: gridDocument,
    loadLibs: loadLibs,
  };
})(window, jQuery);
