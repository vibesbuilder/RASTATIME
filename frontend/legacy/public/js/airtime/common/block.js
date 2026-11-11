/*
 * RASTATIME 2026-11-11 - replaces jQuery BlockUI 2.39 (2011; needed the
 * $.browser shim, CodeQL flagged its HTML building).
 *
 * RASTATIME only ever used BlockUI's element mode: $(el).block({...}) lays
 * a translucent overlay over a panel while it loads (library, show builder,
 * playlist / smart block editor, podcast episode table, the add-show form)
 * and $(el).unblock() takes it away.  This keeps those two calls and the
 * classes BlockUI used (blockUI, blockOverlay, ui-widget-overlay with
 * {theme: true}) so styles.css and the jQuery UI theme style it as before.
 *
 * Options read: theme (jQuery UI overlay classes; without it the BlockUI
 * default black 60 % overlay), message (a plain-text box in the middle;
 * every caller passes "" or null).  BlockUI's other options
 * (applyPlatformOpacityRules, allowBodyStretch, ...) are accepted and
 * ignored.  Loaded on every page (PageLayoutInitPlugin), so a page that
 * forgot to load BlockUI no longer throws.
 */
(function ($) {
  "use strict";

  var FADE_IN = 200; // BlockUI defaults
  var FADE_OUT = 400;
  var BASE_Z = 1000;

  $.fn.block = function (opts) {
    opts = opts || {};
    return this.each(function () {
      var $el = $(this);
      // a second block() replaces the first instead of stacking overlays
      $el.children(".blockUI").stop(true, true).remove();
      if ($el.css("position") === "static") {
        // the overlay is absolutely positioned inside the element
        this.style.position = "relative";
      }

      var $overlay = $("<div/>")
        .addClass("blockUI blockOverlay")
        .css({
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          margin: 0,
          padding: 0,
          border: "none",
          zIndex: BASE_Z,
          cursor: "wait",
          display: "none",
        });
      if (opts.theme) {
        $overlay.addClass("ui-widget-overlay");
      } else {
        $overlay.css({ backgroundColor: "#000", opacity: 0.6 });
      }
      $overlay.appendTo($el).fadeIn(FADE_IN);

      if (typeof opts.message === "string" && opts.message !== "") {
        $("<div/>")
          .addClass("blockUI blockMsg blockElement")
          .css({
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: BASE_Z + 10,
            padding: "8px 16px",
            cursor: "wait",
          })
          .text(opts.message)
          .appendTo($el)
          .hide()
          .fadeIn(FADE_IN);
      }
    });
  };

  $.fn.unblock = function () {
    return this.each(function () {
      $(this)
        .children(".blockUI")
        .stop(true)
        .fadeOut(FADE_OUT, function () {
          $(this).remove();
        });
    });
  };
})(jQuery);
