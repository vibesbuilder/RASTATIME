$(document).ready(function () {
  $.ajaxSetup({
    cache: false,
  });
});

// RASTATIME 2026-10-25 (role audit package 3, R12) - every same-origin
// jQuery write carries the session's CSRF token (CSRF_TOKEN, set by the
// page); the server compares it centrally (Acl_plugin).
$.ajaxPrefilter(function (options, originalOptions, jqXHR) {
  var method = String(options.type || options.method || "GET").toUpperCase();
  if (
    typeof CSRF_TOKEN === "string" &&
    CSRF_TOKEN !== "" &&
    !options.crossDomain &&
    method !== "GET" &&
    method !== "HEAD" &&
    method !== "OPTIONS"
  ) {
    jqXHR.setRequestHeader("X-CSRF-Token", CSRF_TOKEN);
  }
});
