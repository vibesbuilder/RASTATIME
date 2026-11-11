var AIRTIME = (function (AIRTIME) {
  var mod;

  if (AIRTIME.schedule === undefined) {
    AIRTIME.schedule = {};
  }
  mod = AIRTIME.schedule;

  return AIRTIME;
})(AIRTIME || {});

var serverTimezoneOffset = 0;

function closeDialogCalendar(event, ui) {
  $el = $(this);
  $el.dialog("destroy");
  $el.remove();

  //need to refetch the events to update scheduled status.
  scheduleCalRefetch();
}

// RASTATIME 2026-10-20 - the calendar dialogs get LibreTime's stronger,
// lighter backdrop (styles.css .schedule-tracks-overlay).  jQuery UI
// creates the overlay outside the dialog before it fires "open", and its
// `classes` option does not reach it, so the class is added here.
function markScheduleDialogOverlay() {
  var instance = $(this).dialog("instance");
  if (instance && instance.overlay) {
    instance.overlay.addClass("schedule-tracks-overlay");
  }
}

function confirmCancelShow(show_instance_id) {
  if (confirm($.i18n._("Cancel Current Show?"))) {
    var url = baseUrl + "Schedule/cancel-current-show";
    $.ajax({
      url: url,
      data: { format: "json", id: show_instance_id },
      success: function (data) {
        scheduleRefetchEvents(data);
      },
    });
  }
}

function confirmCancelRecordedShow(show_instance_id) {
  if (confirm($.i18n._("Stop recording current show?"))) {
    var url = baseUrl + "Schedule/cancel-current-show";
    $.ajax({
      url: url,
      data: { format: "json", id: show_instance_id },
      success: function (data) {
        scheduleRefetchEvents(data);
      },
    });
  }
}

function findViewportDimensions() {
  var viewportwidth, viewportheight;

  // the more standards compliant browsers (mozilla/netscape/opera/IE7) use
  // window.innerWidth and window.innerHeight
  if (typeof window.innerWidth != "undefined") {
    (viewportwidth = window.innerWidth), (viewportheight = window.innerHeight);
  }
  // IE6 in standards compliant mode (i.e. with a valid doctype as the first
  // line in the document)
  else if (
    typeof document.documentElement != "undefined" &&
    typeof document.documentElement.clientWidth != "undefined" &&
    document.documentElement.clientWidth != 0
  ) {
    viewportwidth = document.documentElement.clientWidth;
    viewportheight = document.documentElement.clientHeight;
  }
  // older versions of IE
  else {
    viewportwidth = document.getElementsByTagName("body")[0].clientWidth;
    viewportheight = document.getElementsByTagName("body")[0].clientHeight;
  }

  return {
    width: viewportwidth,
    height: viewportheight - 45,
  };
}

function highlightMediaTypeSelector(dialog) {
  // RASTATIME 2026-05-17 — when the Schedule Tracks dialog opens, the
  // operator almost always wants to pick file tracks first.  The
  // upstream behaviour fell back to whatever `location.hash` had been
  // set to most recently in the Library view (e.g. `#playlists`), so
  // a previous Library navigation would persist into the dialog.
  // Force the hash to `#tracks` so the dialog always starts on the
  // Tracks tab regardless of where the operator was before.
  if (location.hash !== "#tracks") {
    // Use history.replaceState to avoid a duplicate hashchange event
    // (the listener installed below would otherwise fire twice).
    if (history.replaceState) {
      history.replaceState(null, "", "#tracks");
    } else {
      location.hash = "#tracks";
    }
  }
  var selected = dialog.find("a[href$='#tracks']");

  selected.parent().addClass("selected");
  $("#library_filter").text(selected.text());

  // Slightly hacky way of triggering the click event when it's outside of the anchor text
  dialog.find(".media_type_selector").on("click", function () {
    // Need get(0) here so we don't create a stack overflow by recurring the click on the parent
    $(this).find("a").get(0).click();
  });

  $(window).on("hashchange", function () {
    // RASTATIME 2026-10-21 - only the dialog's own tabs (#tracks,
    // #playlists, ...) switch the media type.  A toolbar link with
    // href="#" (Select all / Select none) empties the hash, and
    // a[href$=''] then matched EVERY anchor: all tabs got .selected and
    // the first one, Tracks, won the next fetch - the library jumped
    // back to Tracks after "Select all" (operator 2026-10-21).
    var selected = location.hash
      ? dialog.find(".media_type_selector a[href$='" + location.hash + "']")
      : $();
    if (selected.length !== 1) {
      return;
    }
    AIRTIME.library.selectNone();
    dialog.find(".media_type_selector").each(function () {
      $(this).removeClass("selected");
    });
    $("#library_filter").text(selected.text());
    selected.parent().addClass("selected");
    // RASTATIME 2026-08-31: was `oTable.fnDraw()` — but oTable is a
    // library.js MODULE-scoped variable, never a global, so every tab
    // click died here with a ReferenceError and the library table
    // silently stayed on the previous media type.  Route the redraw
    // through the public API instead (same pattern as
    // main_builder.js); setCurrentTable() re-queries with the media
    // type of the new hash.  The dialog has no Podcasts tab, so the
    // table type is always LIBRARY.
    AIRTIME.library.setCurrentTable(AIRTIME.library.DataTableTypeEnum.LIBRARY);
  });
}

function buildTimerange(dialog) {
  var builder = dialog.find("#show_builder"),
    oBaseDatePickerSettings = {
      dateFormat: "yy-mm-dd",
      //i18n_months, i18n_days_short are in common.js
      monthNames: i18n_months,
      dayNamesMin: i18n_days_short,
      onClick: function (sDate, oDatePicker) {
        $(this).datepicker("setDate", sDate);
      },
      onClose: validateTimeRange,
    };

  /*
   * Icon hover states for search.
   */
  builder.on("mouseenter", ".sb-timerange .ui-button", function (ev) {
    $(this).addClass("ui-state-hover");
  });
  builder.on("mouseleave", ".sb-timerange .ui-button", function (ev) {
    $(this).removeClass("ui-state-hover");
  });

  builder.find(dateStartId).datepicker(oBaseDatePickerSettings);
  // RASTATIME 2026-11-11 - native time fields (common/time-input.js) instead of the jQuery UI timepicker
  builder.find(timeStartId).rtTimeInput({ onChange: validateTimeRange });
  builder.find(dateEndId).datepicker(oBaseDatePickerSettings);
  builder.find(timeEndId).rtTimeInput({ onChange: validateTimeRange });

  var oRange = AIRTIME.utilities.fnGetScheduleRange(
    dateStartId,
    timeStartId,
    dateEndId,
    timeEndId,
  );
  AIRTIME.showbuilder.fnServerData.start = oRange.start;
  AIRTIME.showbuilder.fnServerData.end = oRange.end;
}

function buildScheduleDialog(json, instance_id) {
  var dialog = $(json.dialog),
    viewport = findViewportDimensions(),
    height = Math.floor(viewport.height * 0.96),
    width = Math.floor(viewport.width * 0.96),
    fnServer = AIRTIME.showbuilder.fnServerData;

  dialog.dialog({
    autoOpen: false,
    title: json.title,
    width: width,
    height: height,
    resizable: false,
    draggable: true,
    modal: true,
    // RASTATIME 2026-08-31: CSS hook for the dark dialog theme
    // (frame + buttonpane #2f2f2f — see styles.css).
    classes: { "ui-dialog": "schedule-tracks-dialog" },
    open: markScheduleDialogOverlay,
    close: closeDialogCalendar,
    buttons: [
      {
        text: $.i18n._("Ok"),
        class: "btn",
        click: function () {
          $(this).dialog("close");
          //getUsabilityHint();
        },
      },
    ],
  });

  //set the start end times so the builder datatables knows its time range.
  fnServer.start = json.start;
  fnServer.end = json.end;
  fnServer.ops = {};
  fnServer.ops.showFilter = 0;
  fnServer.ops.showInstanceFilter = instance_id;
  fnServer.ops.myShows = 0;

  // RASTATIME 2026-05-17 — force the Library tab back to Tracks
  // BEFORE libraryInit + builderDataTable run.  The DataTable's
  // server-data callback reads the filter from
  // $(".media_type_selector.selected").data("selection-id") on
  // every fetch (library.js around line 1022), so we need TWO
  // things in place before libraryInit runs:
  //   (a) location.hash = #tracks  (cleans up any leftover hash
  //       that the operator's previous Library navigation left
  //       in place — also used by the highlightMediaTypeSelector
  //       function below);
  //   (b) the .selected class moved to the #tracks tab inside
  //       the dialog, so the very first fnServerData call sends
  //       type=1 (FILE) instead of e.g. type=2 (PLAYLIST).
  // The visual highlighting + window.hashchange listener
  // installation are still left to highlightMediaTypeSelector
  // below; this block only handles the "initial filter" race.
  if (window.history && history.replaceState) {
    history.replaceState(null, "", "#tracks");
  } else {
    location.hash = "#tracks";
  }
  dialog.find(".media_type_selector").removeClass("selected");
  dialog.find("a[href$='#tracks']").parent().addClass("selected");

  AIRTIME.library.libraryInit();
  AIRTIME.showbuilder.builderDataTable();

  dialog.dialog("open");
  highlightMediaTypeSelector(dialog);
  buildTimerange(dialog);
}

// RASTATIME 2026-10-16 - teaser automation stage 2: the "Teasers" dialog of a
// show (schedule/teaser-dialog); the view's inline script does the work.
function buildTeaserDialog(json) {
  if (typeof json === "string") {
    try {
      json = JSON.parse(json);
    } catch (e) {
      alert("Teasers: unexpected response - " + json.substring(0, 160));
      return;
    }
  }
  if (!json || json.show_error == true) {
    alertShowErrorAndReload();
    return;
  }
  if (!json.dialog) {
    alert("Teasers: the server sent no dialog - " + JSON.stringify(json).substring(0, 160));
    return;
  }
  var dialog = $(json.dialog),
    viewport = findViewportDimensions(),
    width = Math.min(820, (viewport.width * 4) / 5);

  dialog.dialog({
    autoOpen: false,
    title: $.i18n._("Teasers of show") + " '" + json.showTitle + "'",
    width: width,
    height: "auto",
    modal: true,
    classes: { "ui-dialog": "schedule-tracks-dialog" },
    open: markScheduleDialogOverlay,
    close: closeDialogCalendar,
    buttons: [
      {
        text: $.i18n._("Close"),
        class: "btn",
        click: function () {
          dialog.remove();
        },
      },
    ],
  });
  dialog.dialog("open");
}

// RASTATIME 2026-11-03 - archiving stage 1: the "Archive Online" dialog of a show
// instance (schedule/episode-dialog); the view's inline script saves on the
// "rt-episode-save" event and uploads the image itself.
function buildEpisodeDialog(json) {
  if (typeof json === "string") {
    try {
      json = JSON.parse(json);
    } catch (e) {
      alert("Episode: unexpected response - " + json.substring(0, 160));
      return;
    }
  }
  if (!json || json.show_error == true) {
    alertShowErrorAndReload();
    return;
  }
  if (!json.dialog) {
    alert("Episode: the server sent no dialog - " + JSON.stringify(json).substring(0, 160));
    return;
  }
  var dialog = $(json.dialog),
    viewport = findViewportDimensions(),
    width = Math.min(760, (viewport.width * 9) / 10),
    buttons = [];

  if (dialog.data("can-edit") == 1 && dialog.find("#episode_form").length) {
    buttons.push({
      text: $.i18n._("Save"),
      class: "btn btn-new",
      click: function () {
        dialog.trigger("rt-episode-save");
      },
    });
  }
  buttons.push({
    text: $.i18n._("Close"),
    class: "btn",
    click: function () {
      dialog.remove();
    },
  });

  dialog.dialog({
    autoOpen: false,
    title:
      $.i18n._("Archive Online") + " '" + json.showTitle + "' " + (json.startsLocal || ""),
    width: width,
    height: "auto",
    modal: true,
    classes: { "ui-dialog": "schedule-tracks-dialog" },
    open: markScheduleDialogOverlay,
    close: closeDialogCalendar,
    buttons: buttons,
  });
  dialog.dialog("open");
}

// RASTATIME 2026-11-10 - the "People Involved" dialog of an episode
// (schedule/people-dialog, calendar → Extras): the guests of the episode;
// the view's inline script saves on "rt-people-save".
function buildPeopleDialog(json) {
  if (typeof json === "string") {
    try {
      json = JSON.parse(json);
    } catch (e) {
      alert("People Involved: unexpected response - " + json.substring(0, 160));
      return;
    }
  }
  if (!json || json.show_error == true) {
    alertShowErrorAndReload();
    return;
  }
  var dialog = $(json.dialog),
    buttons = [];

  if (dialog.data("can-edit") == 1 && dialog.find("#people_form").length) {
    buttons.push({
      text: $.i18n._("Save"),
      class: "btn btn-new",
      click: function () {
        dialog.trigger("rt-people-save");
      },
    });
  }
  buttons.push({
    text: $.i18n._("Close"),
    class: "btn",
    click: function () {
      dialog.remove();
    },
  });

  dialog.dialog({
    autoOpen: false,
    title:
      $.i18n._("People Involved") + " '" + json.showTitle + "' " + (json.startsLocal || ""),
    width: Math.min(480, (findViewportDimensions().width * 9) / 10),
    height: "auto",
    modal: true,
    classes: { "ui-dialog": "schedule-tracks-dialog" },
    open: markScheduleDialogOverlay,
    close: closeDialogCalendar,
    buttons: buttons,
  });
  dialog.dialog("open");
}

function buildContentDialog(json) {
  var dialog = $(json.dialog),
    viewport = findViewportDimensions(),
    height = (viewport.height * 2) / 3,
    width = (viewport.width * 4) / 5;

  if (json.show_error == true) {
    alertShowErrorAndReload();
  }

  dialog.find("#show_progressbar").progressbar({
    value: json.percentFilled,
  });

  dialog.dialog({
    autoOpen: false,
    title: $.i18n._("Contents of Show") + " '" + json.showTitle + "'",
    width: width,
    height: height,
    modal: true,
    // RASTATIME 2026-08-31: same dark-frame hook as the Schedule
    // Tracks dialog (they share the redmond near-white otherwise).
    classes: { "ui-dialog": "schedule-tracks-dialog" },
    open: markScheduleDialogOverlay,
    close: closeDialogCalendar,
    buttons: [
      {
        text: $.i18n._("Ok"),
        class: "btn",
        click: function () {
          dialog.remove();
        },
      },
    ],
  });

  dialog.dialog("open");
}

/**
 * Use user preference for time scale; defaults to month if preference was never set
 */
function getTimeScalePreference(data) {
  return data.calendarInit.timeScale;
}

/**
 * Use user preference for time interval; defaults to 30m if preference was never set
 */
function getTimeIntervalPreference(data) {
  return parseInt(data.calendarInit.timeInterval);
}

function createFullCalendar(data) {
  serverTimezoneOffset = data.calendarInit.timezoneOffset;

  // RASTATIME 2026-09-17 (JS-modernization): the FC1.5 fork is gone -
  // FullCalendar 6 (buildScheduleFc6() in schedule-fc6.js) is the only
  // Schedule calendar.  The guard only reports a broken deployment
  // (schedule-fc6.js failed to load) instead of silently doing nothing.
  if (typeof buildScheduleFc6 !== "function") {
    console.error(
      "schedule-fc6.js did not load - the Schedule calendar cannot start.",
    );
    return;
  }
  buildScheduleFc6(data);
}

//Alert the error and reload the page
//this function is used to resolve concurrency issue
function alertShowErrorAndReload() {
  alert($.i18n._("The episode doesn't exist anymore!"));
  window.location.reload();
}

$(document).ready(function () {
  $.contextMenu({
    // RASTATIME 2026-06-01 (JS-modernization stage 2): ".fc-event" (not
    // "div.fc-event") so this also matches FullCalendar 6 events, which are
    // <a class="fc-event"> anchors rather than FC1.5's <div>.  FC1.5 events
    // still match, so the fallback is unaffected.  The build() reads the
    // instance via $el.data("event"), which both paths set (FC6 in
    // eventDidMount, schedule-fc6.js).
    selector: ".fc-event",
    trigger: "left",
    ignoreRightClick: true,
    className: "calendar-context-menu",

    build: function ($el, e) {
      var data, items, callback;

      data = $el.data("event");

      function processMenuItems(oItems) {
        //define a schedule callback.
        if (oItems.schedule !== undefined) {
          callback = function () {
            $.post(
              oItems.schedule.url,
              { format: "json", id: data.id },
              function (json) {
                buildScheduleDialog(json, data.id);
              },
            );
          };

          oItems.schedule.callback = callback;
        }

        //define a clear callback.
        if (oItems.clear !== undefined) {
          callback = function () {
            if (confirm($.i18n._("Remove all content?"))) {
              $.post(
                oItems.clear.url,
                { format: "json", id: data.id },
                function (json) {
                  scheduleRefetchEvents(json);
                },
              );
            }
          };
          oItems.clear.callback = callback;
        }

        //define an edit callback.
        if (oItems.edit !== undefined) {
          if (oItems.edit.items !== undefined) {
            var edit = oItems.edit.items;

            //edit a single instance
            callback = function () {
              $.get(
                edit.instance.url,
                {
                  format: "json",
                  showId: data.showId,
                  instanceId: data.id,
                  type: "instance",
                },
                function (json) {
                  beginEditShow(json);
                },
              );
            };
            edit.instance.callback = callback;

            //edit this instance and all
            callback = function () {
              $.get(
                edit.all.url,
                {
                  format: "json",
                  showId: data.showId,
                  instanceId: data.id,
                  type: "all",
                },
                function (json) {
                  beginEditShow(json);
                },
              );
            };
            edit.all.callback = callback;
          } else {
            callback = function () {
              $.get(
                oItems.edit.url,
                {
                  format: "json",
                  showId: data.showId,
                  instanceId: data.id,
                  type: oItems.edit._type,
                },
                function (json) {
                  beginEditShow(json);
                },
              );
            };
            oItems.edit.callback = callback;
          }
        }

        //define a content callback.
        if (oItems.content !== undefined) {
          callback = function () {
            $.get(
              oItems.content.url,
              { format: "json", id: data.id },
              function (json) {
                buildContentDialog(json);
              },
            );
          };
          oItems.content.callback = callback;
        }

        // RASTATIME 2026-11-10 - Teasers and Archive Online sit in the
        // "Extras" submenu (CalendarService::addExtrasItem).
        var extras = oItems.extras !== undefined && oItems.extras.items ? oItems.extras.items : oItems;

        // RASTATIME 2026-10-16 - teaser automation stage 2: "Teasers" dialog
        if (extras.teasers !== undefined) {
          callback = function () {
            $.get(
              extras.teasers.url,
              { format: "json", id: data.id },
              function (json) {
                buildTeaserDialog(json);
              },
            );
          };
          extras.teasers.callback = callback;
        }

        // RASTATIME 2026-11-03 - archiving stage 1: "Archive Online" dialog
        if (extras.episode !== undefined) {
          callback = function () {
            $.get(
              extras.episode.url,
              { format: "json", id: data.id },
              function (json) {
                buildEpisodeDialog(json);
              },
            );
          };
          extras.episode.callback = callback;
        }

        // RASTATIME 2026-11-10 - "People Involved" dialog (guests of the episode)
        if (extras.people !== undefined) {
          callback = function () {
            $.get(
              extras.people.url,
              { format: "json", id: data.id },
              function (json) {
                buildPeopleDialog(json);
              },
            );
          };
          extras.people.callback = callback;
        }

        //define a cancel recorded show callback.
        if (oItems.cancel_recorded !== undefined) {
          callback = function () {
            confirmCancelRecordedShow(data.id);
          };
          oItems.cancel_recorded.callback = callback;
        }

        //define a view recorded callback.
        if (oItems.view_recorded !== undefined) {
          callback = function () {
            $.get(
              oItems.view_recorded.url,
              { format: "json" },
              function (json) {
                //in library.js
                buildEditMetadataDialog(json);
              },
            );
          };
          oItems.view_recorded.callback = callback;
        }

        //define a cancel callback.
        if (oItems.cancel !== undefined) {
          callback = function () {
            confirmCancelShow(data.id);
          };
          oItems.cancel.callback = callback;
        }

        //define a delete callback.
        // RASTATIME 2026-10-28 - the delete no longer goes out at once:
        // rtUndoDelete (undo-delete.js) hides the show, shows a toast with
        // a countdown and an Undo link and posts the same URL when the
        // countdown ends.  Server side unchanged.
        if (oItems.del !== undefined) {
          //repeating show multiple delete options
          if (oItems.del.items !== undefined) {
            var del = oItems.del.items;

            //delete a single instance
            callback = function () {
              rtUndoDelete.defer(del.single.url, data, "single");
            };
            del.single.callback = callback;

            //delete this instance and all following instances.
            callback = function () {
              rtUndoDelete.defer(del.following.url, data, "following");
            };
            del.following.callback = callback;
          }
          //single show
          else {
            callback = function () {
              rtUndoDelete.defer(oItems.del.url, data, "show");
            };
            oItems.del.callback = callback;
          }
        }

        items = oItems;
      }

      $.ajax({
        url: baseUrl + "schedule/make-context-menu",
        type: "GET",
        data: { instanceId: data.id, showId: data.showId, format: "json" },
        dataType: "json",
        async: false,
        success: function (json) {
          processMenuItems(json.items);
        },
      });

      return {
        className: "calendar-context-menu",
        items: items,
        determinePosition: function ($menu, x, y) {
          $menu
            .css("display", "block")
            .position({
              my: "left top",
              at: "right top",
              of: this,
              offset: "-20 10",
              collision: "fit",
            })
            .css("display", "none");
        },
      };
    },
  });
});
