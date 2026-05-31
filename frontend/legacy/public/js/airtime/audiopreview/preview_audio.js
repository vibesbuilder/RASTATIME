/**
 * RASTATIME 2026-05-31 (JS-modernization stage 0c)
 * ------------------------------------------------------------------
 * Vanilla, native-<audio> replacement for the jPlayerPlaylist-based
 * audio preview.  Supersedes preview_jplayer.js + jplayer.playlist.min.js
 * + the jPlayer skin CSS (jPlayer 2.7.0 is maintained-archived since 2018).
 *
 * Runs inside the popup window opened by common.js (openPreviewWindow).
 * The native <audio controls> element provides play/pause/seek/volume/
 * mute/time for free; this module only adds playlist management
 * (next/prev, ended -> next, click-to-play list) on top.
 *
 * It preserves the global function names the MAIN window calls on the
 * popup (via _preview_window.<fn>) so common.js stays unchanged:
 *     playAllPlaylist(playlistID, playlistIndex)
 *     playBlock(blockId, blockIndex)
 *     playAllShow(showID, showIndex)
 * plus stopPreview() used by spl.js stopAudioPreview().
 *
 * Depends only on two globals already present on the page:
 *   baseUrl            (set by PageLayoutInitPlugin)
 *   isAudioSupported() (audioplaytest.js — native canPlayType check)
 */
(function () {
  "use strict";

  var URL_BAR_HEIGHT = 32;

  var audioEl = null; // the <audio> element
  var playlist = []; // [{title, artist, uri, mime}]
  var current = -1;
  var idToPosition = {}; // server element_id -> playlist index

  function $one(sel) {
    return document.querySelector(sel);
  }

  function spanText(cls) {
    var el = document.querySelector(cls);
    return el ? el.textContent.trim() : "";
  }

  function getAudio() {
    if (!audioEl) {
      audioEl = $one("#preview_audio_el");
    }
    return audioEl;
  }

  function updateNowPlaying() {
    var info = $one("#preview_nowplaying");
    if (!info) {
      return;
    }
    var item = playlist[current];
    if (!item) {
      info.textContent = "";
      return;
    }
    info.textContent = item.artist
      ? item.title + " — " + item.artist
      : item.title || "";
  }

  function renderPlaylistUi() {
    var ul = $one("#preview_playlist");
    var nav = $one("#preview_nav");
    // Single-track previews (one file / one stream) hide the playlist UI.
    var multi = playlist.length > 1;
    if (nav) {
      nav.style.display = multi ? "" : "none";
    }
    if (!ul) {
      return;
    }
    ul.style.display = multi ? "" : "none";
    ul.innerHTML = "";
    playlist.forEach(function (item, i) {
      var li = document.createElement("li");
      li.textContent =
        (item.title || "(untitled)") + (item.artist ? " — " + item.artist : "");
      li.className = i === current ? "preview-current" : "";
      li.addEventListener("click", function () {
        playAt(i);
      });
      ul.appendChild(li);
    });
  }

  function playAt(i) {
    var a = getAudio();
    if (!a || i < 0 || i >= playlist.length) {
      return;
    }
    current = i;
    a.src = playlist[i].uri;
    a.load();
    var p = a.play();
    if (p && typeof p.catch === "function") {
      // Autoplay may be gated by the browser — the user can press play.
      p.catch(function () {});
    }
    updateNowPlaying();
    renderPlaylistUi();
  }

  function next() {
    if (current + 1 < playlist.length) {
      playAt(current + 1);
    }
  }

  function prev() {
    if (current - 1 >= 0) {
      playAt(current - 1);
    }
  }

  function stopPreview() {
    var a = getAudio();
    if (a) {
      a.pause();
      try {
        a.currentTime = 0;
      } catch (e) {
        /* not seekable yet */
      }
    }
  }

  function setPlaylist(items) {
    playlist = items || [];
    current = -1;
    renderPlaylistUi();
  }

  function playByElementIndex(elementIndex) {
    var pos = idToPosition[elementIndex];
    if (pos === undefined) {
      pos = 0;
    }
    playAt(pos);
  }

  // Build the playlist from a server JSON endpoint
  // (audiopreview/get-playlist | get-show | get-block).
  function buildPlaylist(url, playIndex) {
    idToPosition = {};
    fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var items = [];
        var pos = 0;
        Object.keys(data).forEach(function (k) {
          var d = data[k];
          var mime = d.mime || "";
          if (typeof isAudioSupported === "function" && mime && !isAudioSupported(mime)) {
            return; // skip browser-unsupported track
          }
          items.push({
            title: d.element_title,
            artist: d.element_artist,
            uri: d.uri,
            mime: mime,
          });
          idToPosition[d.element_id] = pos;
          pos++;
        });
        setPlaylist(items);
        playByElementIndex(playIndex);
        resizeToContent();
      })
      .catch(function (e) {
        console.error("audio preview: failed to load playlist", e);
      });
  }

  function playOne(uri, mime) {
    var title = spanText(".audioFileTitle");
    var artist = spanText(".audioFileArtist");
    if (title === "null") {
      title = "";
    }
    if (artist === "null") {
      artist = "";
    }
    setPlaylist([{ title: title, artist: artist, uri: uri, mime: mime }]);
    playAt(0);
    resizeToContent();
  }

  function resizeToContent() {
    var c = $one("#jp_container_1") || document.body;
    try {
      window.resizeTo(
        Math.max(c.offsetWidth + 2, 480),
        c.offsetHeight + URL_BAR_HEIGHT + 2,
      );
    } catch (e) {
      /* popup may not allow resize */
    }
  }

  // ---- Globals the MAIN window calls on the popup (_preview_window.*) ------
  window.playAllPlaylist = function (playlistID, playlistIndex) {
    var viewsId = spanText(".playlistID");
    if (Object.keys(idToPosition).length && viewsId == playlistID) {
      playByElementIndex(playlistIndex);
    } else {
      buildPlaylist(
        baseUrl + "audiopreview/get-playlist/playlistID/" + playlistID,
        playlistIndex,
      );
    }
  };

  window.playBlock = function (blockId, blockIndex) {
    var viewsId = spanText(".blockId");
    if (Object.keys(idToPosition).length && viewsId == blockId) {
      playByElementIndex(blockIndex);
    } else {
      buildPlaylist(
        baseUrl + "audiopreview/get-block/blockId/" + blockId,
        blockIndex,
      );
    }
  };

  window.playAllShow = function (showID, showIndex) {
    var viewsId = spanText(".showID");
    if (Object.keys(idToPosition).length && viewsId == showID) {
      playByElementIndex(showIndex);
    } else {
      buildPlaylist(
        baseUrl + "audiopreview/get-show/showID/" + showID,
        showIndex,
      );
    }
  };

  window.stopPreview = stopPreview;

  // ---- Initial playback when the popup first loads -------------------------
  document.addEventListener("DOMContentLoaded", function () {
    audioEl = $one("#preview_audio_el");
    if (audioEl) {
      audioEl.addEventListener("ended", next);
    }
    var nextBtn = $one("#preview_next");
    var prevBtn = $one("#preview_prev");
    if (nextBtn) {
      nextBtn.addEventListener("click", next);
    }
    if (prevBtn) {
      prevBtn.addEventListener("click", prev);
    }

    var audioUri = spanText(".audioUri");
    var audioMime = spanText(".audioMime");
    var playlistID = spanText(".playlistID");
    var playlistIndex = spanText(".playlistIndex");
    var showID = spanText(".showID");
    var showIndex = spanText(".showIndex");
    var blockId = spanText(".blockId");
    var blockIndex = spanText(".blockIndex");

    if (playlistID !== "") {
      window.playAllPlaylist(playlistID, playlistIndex);
    } else if (audioUri !== "") {
      playOne(audioUri, audioMime);
    } else if (showID !== "") {
      window.playAllShow(showID, showIndex);
    } else if (blockId !== "" && blockIndex !== "") {
      window.playBlock(blockId, blockIndex);
    }
  });
})();
