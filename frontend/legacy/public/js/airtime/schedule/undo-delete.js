/**
 * RASTATIME 2026-10-28 - "Undo" for a few seconds after deleting a show
 * from the calendar (BACKLOG "Rueckgaengig nach Loeschen", variant A).
 *
 * The calendar's context menu used to POST the delete at once (no
 * confirmation at all).  Now the click only hides the affected show
 * chips and shows a toast with a countdown and an Undo link; the real
 * POST (schedule/delete-show-instance or schedule/delete-show, unchanged
 * on the server) goes out when the countdown ends.  Undo drops the
 * pending request and shows the chips again - nothing was changed.
 *
 * Fail-safe direction: whatever goes wrong before the POST, the show is
 * NOT deleted and reappears on the next refetch.  Leaving the page while
 * a delete is pending sends it as a beacon (CSRF token in the body, the
 * same pattern as the page-layout save in common.js), so a user who
 * closes the tab inside the countdown still gets the delete they asked
 * for.
 *
 * Hiding is done by class: every chip of a pending instance carries
 * `rt-pending-delete` (display:none in schedule-fc6.css).  FC6 re-renders
 * chips on its own (resize, now-playing refresh), so schedule-fc6.js's
 * eventDidMount asks isPending() and re-applies the class.
 *
 * Modes: "single" hides one instance; "following" hides every instance
 * of the same show that starts at or after the clicked one; "show" hides
 * every instance of the show (the server deletes from the clicked
 * instance on, past instances cannot be deleted anyway).
 */
window.rtUndoDelete = (function ($) {
  "use strict";

  var DELAY_SECONDS = 10;
  var pending = {}; // key -> job
  var seq = 0;

  function containerEl() {
    var $c = $("#rt-undo-toasts");
    if ($c.length === 0) {
      $c = $('<div id="rt-undo-toasts" role="status" aria-live="polite"></div>').appendTo("body");
    }
    return $c;
  }

  /** Instance ids the delete will cover - for hiding only, the server decides. */
  function affectedIds(mode, event) {
    var ids = [String(event.id)];
    if (mode === "single" || !window.scheduleFc6 || typeof window.scheduleFc6.getEvents !== "function") {
      return ids;
    }
    var clicked = window.scheduleFc6.getEventById(String(event.id));
    var from = clicked && clicked.start ? clicked.start.getTime() : null;
    $.each(window.scheduleFc6.getEvents(), function (_, ev) {
      var p = ev.extendedProps || {};
      if (String(p.showId) !== String(event.showId) || String(ev.id) === String(event.id)) {
        return;
      }
      if (mode === "show" || from === null || (ev.start && ev.start.getTime() >= from)) {
        ids.push(String(ev.id));
      }
    });
    return ids;
  }

  function setHidden(ids, hidden) {
    $.each(ids, function (_, id) {
      $(".fc-show-instance-" + id).toggleClass("rt-pending-delete", hidden);
    });
  }

  function isPending(instanceId) {
    var id = String(instanceId);
    var found = false;
    $.each(pending, function (_, job) {
      if (job.ids.indexOf(id) !== -1) {
        found = true;
        return false;
      }
    });
    return found;
  }

  function messageFor(mode, title) {
    var text;
    if (mode === "following") {
      text = $.i18n._('Deleting "%s" and all following episodes in %s s');
    } else if (mode === "show") {
      text = $.i18n._('Deleting the show "%s" in %s s');
    } else {
      text = $.i18n._('Deleting "%s" in %s s');
    }
    return text.replace("%s", title || $.i18n._("this show"));
  }

  function postData(job) {
    return { format: "json", id: job.event.id };
  }

  function commit(job) {
    if (!pending[job.key]) {
      return;
    }
    delete pending[job.key];
    job.$toast.remove();
    $.post(job.url, postData(job), function (json) {
      if (typeof scheduleRefetchEvents === "function") {
        scheduleRefetchEvents(json);
      }
    }).fail(function () {
      // the server did not take it: show the chips again, nothing is lost
      setHidden(job.ids, false);
      if (typeof scheduleCalRefetch === "function") {
        scheduleCalRefetch();
      }
    });
  }

  function undo(job) {
    if (!pending[job.key]) {
      return;
    }
    clearInterval(job.timer);
    delete pending[job.key];
    job.$toast.remove();
    setHidden(job.ids, false);
  }

  /**
   * Hide the show, start the countdown.  `event` is the chip's
   * $el.data("event") ({id, showId, linked, title}); `mode` is
   * "single" | "following" | "show"; `url` the delete action.
   */
  function defer(url, event, mode) {
    var job = {
      key: "d" + ++seq,
      url: url,
      event: event,
      mode: mode,
      ids: affectedIds(mode, event),
      left: DELAY_SECONDS,
    };
    setHidden(job.ids, true);

    var $msg = $('<span class="rt-undo-text"></span>').text(messageFor(mode, event.title).replace("%s", job.left));
    var $undo = $('<a href="#" class="rt-undo-link"></a>').text($.i18n._("Undo"));
    job.$toast = $('<div class="rt-undo-toast"></div>').append($msg).append($undo).appendTo(containerEl());

    $undo.on("click", function (e) {
      e.preventDefault();
      undo(job);
    });
    job.timer = setInterval(function () {
      job.left -= 1;
      if (job.left <= 0) {
        clearInterval(job.timer);
        commit(job);
        return;
      }
      $msg.text(messageFor(mode, event.title).replace("%s", job.left));
    }, 1000);
    pending[job.key] = job;
    return job.key;
  }

  /** Leaving the page: send every pending delete as a beacon. */
  function flushAll() {
    $.each(pending, function (key, job) {
      clearInterval(job.timer);
      job.$toast.remove();
      if (navigator.sendBeacon) {
        var body = new URLSearchParams(postData(job));
        if (typeof CSRF_TOKEN === "string") {
          body.append("csrf_token", CSRF_TOKEN);
        }
        navigator.sendBeacon(job.url, body);
      }
    });
    pending = {};
  }

  $(window).on("pagehide", flushAll);

  return {
    defer: defer,
    isPending: isPending,
    flushAll: flushAll,
    pendingCount: function () {
      return Object.keys(pending).length;
    },
    DELAY_SECONDS: DELAY_SECONDS,
  };
})(jQuery);
