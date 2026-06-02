/**
 * RASTATIME 2026-06-01 (JS-modernization stage 2): $.browser polyfill.
 * ------------------------------------------------------------------------------
 * jQuery removed $.browser in 1.9 and jquery-migrate 3 no longer restores it, but
 * several vendored 2011-era plugins still read it and throw on jQuery 3:
 *   - blockUI      (jquery.blockUI.js):     $.browser.msie / .version
 *   - contextMenu  (jquery.contextMenu.js): $.browser.msie / .mozilla
 *   - the jQuery-UI timepicker addon:       $.browser.msie
 *
 * Restore a minimal $.browser so those reads do not throw.  Modern browsers
 * report msie:false, so the legacy IE-only code paths are simply skipped.
 *
 * Loaded only on the ?jq3 path, right after jquery-migrate and before any plugin.
 * A no-op on jQuery 1.8 (which still ships $.browser) and idempotent.
 */
(function ($) {
  if (!$ || $.browser) {
    return;
  }
  var ua = (navigator.userAgent || "").toLowerCase();
  var verMatch = /(?:msie |rv:|firefox\/|chrome\/|version\/|opr\/)([\d.]+)/.exec(
    ua,
  );
  $.browser = {
    msie: /msie |trident\//.test(ua),
    mozilla: /firefox\//.test(ua),
    webkit: /webkit\//.test(ua),
    opera: /opera|opr\//.test(ua),
    version: verMatch ? verMatch[1] : "0",
  };
})(window.jQuery);
