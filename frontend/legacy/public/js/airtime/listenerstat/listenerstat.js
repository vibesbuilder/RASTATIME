$(document).ready(function () {
  listenerstat_content = $("#listenerstat_content");
  (dateStartId = "#his_date_start"),
    (timeStartId = "#his_time_start"),
    (dateEndId = "#his_date_end"),
    (timeEndId = "#his_time_end");

  // set width dynamically
  var width = $("#listenerstat_content").width();
  width = width * 0.91;
  $("#listenerstat_content").find("#flot_placeholder").width(width);
  $("#listenerstat_content").find("#legend").width(width);

  // RASTATIME 2026-11-11 - date / time fields set up once here (they were
  // re-initialised in plot() on every data load); native time fields
  // (common/time-input.js) instead of the jQuery UI timepicker
  var oBaseDatePickerSettings = {
    dateFormat: "yy-mm-dd",
    //i18n_months, i18n_days_short are in common.js
    monthNames: i18n_months,
    dayNamesMin: i18n_days_short,
    onSelect: function (sDate, oDatePicker) {
      $(this).datepicker("setDate", sDate);
    },
  };
  listenerstat_content.find(dateStartId).datepicker(oBaseDatePickerSettings);
  listenerstat_content.find(timeStartId).rtTimeInput();
  listenerstat_content.find(dateEndId).datepicker(oBaseDatePickerSettings);
  listenerstat_content.find(timeEndId).rtTimeInput();

  getDataAndPlot();

  // RASTATIME 2026-11-11 - bound once (Flot 0.8 code bound it on every redraw)
  var previousPoint = null;
  $("#flot_placeholder").on("plothover", function (event, pos, item) {
    if (!item) {
      $("#tooltip").remove();
      previousPoint = null;
      return;
    }
    var pointKey = item.seriesIndex + ":" + item.dataIndex;
    if (previousPoint === pointKey) {
      return;
    }
    previousPoint = pointKey;
    $("#tooltip").remove();
    $("<div id='tooltip'/>")
      .text(
        sprintf(
          $.i18n._("Listener Count on %s: %s"),
          item.series.label,
          Math.floor(item.datapoint[1]),
        ),
      )
      .css({
        position: "absolute",
        display: "none",
        top: item.pageY + 5,
        left: item.pageX + 5,
        border: "1px solid #fdd",
        padding: "2px",
        "background-color": "#fee",
        opacity: 0.8,
      })
      .appendTo("body")
      .fadeIn(200);
  });

  // redraw when the placeholder changes size (instead of Flot's polling
  // resize plugin)
  if (window.ResizeObserver) {
    new ResizeObserver(function () {
      var $ph = $("#flot_placeholder");
      if (listenerPlot && $ph.width() > 0 && $ph.height() > 0) {
        listenerPlot.resize();
        listenerPlot.setupGrid();
        listenerPlot.draw();
      }
    }).observe(document.getElementById("flot_placeholder"));
  }

  listenerstat_content.find("#his_submit").click(function () {
    var oRange = AIRTIME.utilities.fnGetScheduleRange(
      dateStartId,
      timeStartId,
      dateEndId,
      timeEndId,
    );
    var start = oRange.start;
    var end = oRange.end;
    getDataAndPlot(start, end);
  });
});

/**
 * Toggle a spinner overlay so the user knows the page is processing
 */
function toggleOverlay() {
  $("#flot_placeholder").toggleClass("processing");
}

/**
 * RASTATIME 2026-11-11 - Flot 4.2 instead of 0.8.3.  The timestamps from
 * Listenerstat/get-data are already shifted to the user's timezone on the
 * server (ListenerStat::getDataPointsWithinRange, per sample), so plotting
 * them on Flot's UTC axis shows studio time.
 */
function getDataAndPlot(startTimestamp, endTimestamp) {
  // Turn on the processing overlay
  toggleOverlay();

  // get data
  $.get(
    baseUrl + "Listenerstat/get-data",
    { start: startTimestamp, end: endTimestamp },
    function (data) {
      var out = {};
      $.each(data, function (mpName, v) {
        var plotData = { label: mpName, data: [] };
        $.each(v, function (i, ele) {
          plotData.data.push([ele.timestamp * 1000, ele.listener_count]);
        });
        out[mpName] = plotData;
      });
      plot(out);
      // Turn off the processing overlay
      toggleOverlay();
    },
  );
}

var listenerPlot = null;

function plot(datasets) {
  var names = Object.keys(datasets);
  // a new data set starts with every mount point shown
  var shown = {};
  names.forEach(function (name) {
    shown[name] = true;
  });

  function draw() {
    var first = Infinity;
    var last = -Infinity;
    // Hidden mount points stay in the list with no data, and every series
    // keeps its colour index, so the colours do not shift when one is hidden.
    var data = names.map(function (name, i) {
      var series = datasets[name];
      if (!shown[name]) {
        return { label: name, data: [], color: i };
      }
      if (series.data.length) {
        first = Math.min(first, series.data[0][0]);
        last = Math.max(last, series.data[series.data.length - 1][0]);
      }
      return { label: name, data: series.data, color: i };
    });

    var xaxis = {
      mode: "time",
      timeBase: "milliseconds", // Flot 3+ defaults to seconds
      timeformat: "%y/%m/%d %H:%M", // Flot 4 pads %d itself (no %0d)
      color: "#d6d6d6",
      tickColor: "#d6d6d6",
    };
    var tickSize = (last - first) / 1000 / 10; // about ten ticks
    if (isFinite(tickSize) && tickSize > 0) {
      xaxis.tickSize = [tickSize, "second"];
    }

    listenerPlot = $.plot($("#flot_placeholder"), data, {
      yaxis: {
        min: 0,
        tickDecimals: 0,
        color: "#d6d6d6",
        tickColor: "#d6d6d6",
      },
      xaxis: xaxis,
      grid: {
        hoverable: true,
        backgroundColor: { colors: ["#333", "#555"] },
      },
      series: {
        lines: {
          show: true,
          fill: 0.3,
        },
        points: { show: true },
      },
      legend: { show: false },
    });
    return listenerPlot;
  }

  // The legend is our own markup: a checkbox per mount point to show or
  // hide it.  Mount names are set as text (Flot 0.8's labelFormatter put
  // them into the HTML unescaped).
  function buildLegend(drawn) {
    var $legend = $("#legend").empty();
    drawn.getData().forEach(function (series) {
      var $checkbox = $("<input type='checkbox'/>")
        .addClass("legendCB")
        .prop("checked", !!shown[series.label])
        .on("change", function () {
          shown[series.label] = this.checked;
          draw();
        });
      $("<label/>")
        .css({
          display: "inline-flex",
          alignItems: "center",
          marginRight: "16px",
          color: "#c0c0c0",
          cursor: "pointer",
        })
        .append(
          $checkbox,
          $("<span/>").css({
            display: "inline-block",
            width: "12px",
            height: "12px",
            margin: "0 6px",
            border: "1px solid #ccc",
            background: series.color,
          }),
          $("<span/>").text(series.label),
        )
        .appendTo($legend);
    });
  }

  buildLegend(draw());
}
