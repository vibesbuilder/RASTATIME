/**
 * RASTATIME 2026-06-01 (JS-modernization stage 1)
 * ------------------------------------------------------------------
 * Vanilla/jQuery replacement for the former AngularJS "Publish" controller.
 * No angular.module / $scope / $http / ng-* / angular.bootstrap.  The dialog
 * HTML (library/publish-dialog.phtml) now uses plain ids/classes and is wired
 * up here; data comes from the same REST endpoints as before.
 *
 * The original two-way ng-model bindings are replaced by:
 *   - rendering the (read-only) media fields from the fetched JSON,
 *   - a persistent `publishData` map for the checkbox state (so it survives
 *     the 5s poll), and a signature check so the lists only re-render when the
 *     source data actually changed (no flicker / no lost focus).
 *
 * HTTP parity with the old $http: GET sent no csrf (Angular ignored the 2nd
 * arg), PUT sent a JSON body { csrf_token, sources } — reproduced via $.ajax.
 */
var AIRTIME = (function (AIRTIME) {
  var mod;

  if (AIRTIME.publish === undefined) {
    AIRTIME.publish = {};
  }
  mod = AIRTIME.publish;

  var endpoint = "rest/media/";
  var dialogUrl = "library/publish-dialog";

  function initPublishDialog(mediaId, tab) {
    var view = tab.contents; // jQuery wrapper for this tab's DOM
    var unpublishLabel = view.find(".i18n-unpublish").text() || "Unpublish";
    var media = {};
    var sources = { toPublish: [], published: [] };
    var publishData = {}; // persistent checkbox state across polls
    var lastSig = null;
    var sourceInterval = null;

    function csrf() {
      return jQuery("#csrf").val();
    }

    function renderMedia() {
      view.find(".pub-track-title").text(media.track_title || "");
      view.find(".pub-track-title-input").val(media.track_title || "");
      view.find(".pub-artist-name").val(media.artist_name || "");
      view.find(".pub-description").val(media.description || "");
      view.find(".pub-media-id").val(media.id || "");
      if (media.track_title) {
        tab.setName(media.track_title);
      }
    }

    function renderSources() {
      // Only rebuild the lists when the source/status set changed, so the user
      // doesn't lose checkbox focus on every 5s poll.
      var sig = JSON.stringify(
        sources.toPublish.concat(sources.published).map(function (s) {
          return s.source + ":" + s.status;
        }),
      );
      if (sig === lastSig) {
        return;
      }
      lastSig = sig;

      var $tp = view.find(".pub-topublish-list").empty();
      sources.toPublish.forEach(function (s) {
        var id = "pub_src_" + s.source;
        var $row = jQuery("<div class='publish-sources'></div>");
        $row.append(
          jQuery("<input type='checkbox' name='publish_sources' class='pub-source-cb'>")
            .attr("id", id)
            .attr("data-source", s.source)
            .prop("disabled", s.status == 2)
            .prop("checked", !!publishData[s.source]),
        );
        $row.append(
          jQuery("<label class='source-name'></label>").attr("for", id).text(s.label),
        );
        $tp.append($row);
      });
      view.find(".pub-topublish-empty").toggle(sources.toPublish.length === 0);

      var $pub = view.find(".pub-published-list").empty();
      sources.published.forEach(function (s) {
        var $row = jQuery("<div class='published-sources'></div>");
        $row.append("<span class='sp-checked-icon checked-icon left-floated'></span>");
        $row.append(jQuery("<span class='source-name'></span>").text(s.label));
        $row.append(
          jQuery("<button class='btn btn-small btn-danger pub-unpublish' type='button'></button>")
            .attr("data-source", s.source)
            .prop("disabled", s.status == -1)
            .text(unpublishLabel),
        );
        $pub.append($row);
      });
      view.find(".pub-published-empty").toggle(sources.published.length === 0);

      updatePublishBtn();
    }

    function updatePublishBtn() {
      view
        .find(".pub-publish")
        .prop("disabled", view.find(".pub-source-cb:checked").length === 0);
    }

    function getJson(url) {
      // Force JSON parsing. The REST API returns JSON but not always with an
      // application/json Content-Type; jQuery (unlike Angular's lenient $http)
      // only auto-parses by Content-Type, otherwise it hands back a raw string
      // (which made media.* undefined and jQuery.each() iterate the JSON string
      // character by character). dataType:"json" uses JSON.parse -> no eval,
      // CSP-safe.
      return jQuery.ajax({ url: url, dataType: "json" });
    }

    function fetchSourceData() {
      getJson(endpoint + mediaId).done(function (json) {
        media = json;
        renderMedia();
      });
      // All sources with their translated labels + publication state for the
      // file. |status| == 1 -> already published, else -> available to publish.
      getJson(endpoint + mediaId + "/publish-sources").done(function (json) {
        sources = { toPublish: [], published: [] };
        jQuery.each(json, function () {
          if (Math.abs(this.status) == 1) {
            sources.published.push(this);
          } else {
            sources.toPublish.push(this);
          }
        });
        renderSources();
      });
    }

    function putSources(data, after) {
      jQuery
        .ajax({
          url: endpoint + mediaId + "/publish",
          type: "PUT",
          contentType: "application/json",
          data: JSON.stringify({ csrf_token: csrf(), sources: data }),
        })
        .done(after);
    }

    function publish() {
      var data = {};
      jQuery.each(publishData, function (k, v) {
        if (v) {
          data[k] = "publish";
        }
      });
      if (Object.keys(data).length === 0) {
        return;
      }
      putSources(data, function () {
        view.find(".pub-publish").prop("disabled", true);
        publishData = {}; // reset so re-publishing without closing works
        lastSig = null; // force a re-render after the state change
        fetchSourceData();
      });
    }

    function remove(source) {
      var data = {};
      data[source] = "unpublish";
      putSources(data, function () {
        lastSig = null;
        fetchSourceData();
      });
    }

    function openEditDialog() {
      var uid = AIRTIME.library.MediaTypeStringEnum.FILE + "_" + mediaId;
      jQuery.get(
        baseUrl + "library/edit-file-md/id/" + mediaId,
        { format: "json" },
        function (json) {
          AIRTIME.playlist.fileMdEdit(json, uid);
        },
      );
    }

    function discard() {
      if (tab) {
        tab.close();
      }
    }

    // ---- wire the DOM (delegation survives list re-renders) ------------------
    view.on("change", ".pub-source-cb", function () {
      publishData[jQuery(this).attr("data-source")] = jQuery(this).is(":checked");
      updatePublishBtn();
    });
    view.on("click", ".pub-unpublish", function () {
      remove(jQuery(this).attr("data-source"));
      return false;
    });
    view.find(".pub-edit-md").on("click", function () {
      openEditDialog();
      return false;
    });
    view.find(".pub-publish").on("click", function () {
      publish();
      return false;
    });
    view.find(".pub-close").on("click", function () {
      discard();
      return false;
    });

    // ---- start: fetch + poll every 5s; clean up on tab close -----------------
    fetchSourceData();
    sourceInterval = setInterval(fetchSourceData, 5000);
    tab.assignOnCloseHandler(function () {
      clearInterval(sourceInterval);
    });
  }

  mod.publishSelectedTracks = function () {
    // (was already a no-op in the AngularJS version)
  };

  mod.openPublishDialog = function (mediaId) {
    jQuery.get(dialogUrl, { csrf_token: jQuery("#csrf").val() }).done(function (html) {
      var tab = AIRTIME.tabs.openTab(html, "publish_" + mediaId, null);
      initPublishDialog(mediaId, tab);
    });
  };

  return AIRTIME;
})(AIRTIME || {});
