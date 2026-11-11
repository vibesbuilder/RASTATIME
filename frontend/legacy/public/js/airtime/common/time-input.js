/*
 * RASTATIME 2026-11-11 - native time fields instead of the jQuery UI
 * timepicker 0.2.9 (Francois Gelinas, unmaintained since ~2014, needed the
 * $.browser shim, CodeQL flagged its HTML building).
 *
 *   $(input).rtTimeInput({ onChange: fn })
 *
 * turns a text field into <input type="time" step="60">: the browser's own
 * hour / minute field with keyboard, mouse wheel and picker.  The value
 * stays "HH:MM" (24 h) whatever the browser shows, so forms, validators and
 * AIRTIME.utilities.fnGetScheduleRange (empty = 00:00) are unchanged.  A
 * server value without leading zero ("0:00", "9:05") is padded first - the
 * browser would show an empty field for it.  onChange replaces the old
 * picker's onClose / onSelect callbacks; the browser fires "input" and
 * "change" itself.
 */
(function ($) {
  "use strict";

  function normalize(value) {
    var m = /^\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*$/.exec(value || "");
    if (!m || Number(m[1]) > 23 || Number(m[2]) > 59) {
      return "";
    }
    return (m[1].length === 1 ? "0" : "") + m[1] + ":" + m[2];
  }

  $.fn.rtTimeInput = function (opts) {
    opts = opts || {};
    return this.each(function () {
      var value = normalize(this.value);
      this.type = "time";
      this.step = 60;
      this.value = value;
      var $input = $(this).addClass("rt-time-input");
      if (opts.onChange && !$input.data("rtTimeInputBound")) {
        $input.data("rtTimeInputBound", true).on("change", opts.onChange);
      }
    });
  };

  $.rtTimeInput = { normalize: normalize };
})(jQuery);
