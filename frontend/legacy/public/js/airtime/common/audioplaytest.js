function isAudioSupported(mime) {
  var audio = new Audio();

  if (typeof mime !== "string" || mime === null) {
    return false;
  }

  var bMime = null;
  if (mime.indexOf("ogg") != -1 || mime.indexOf("vorbis") != -1) {
    bMime = 'audio/ogg; codecs="vorbis"';
  } else {
    bMime = mime;
  }

  // RASTATIME 2026-05-31 (JS-modernization stage 0c): the Flash fallback was
  // removed (Flash is dead, jPlayer gone). Native canPlayType is authoritative
  // on modern browsers — mp3/mp4/mpeg all play natively.
  return !!audio.canPlayType && audio.canPlayType(bMime) != "";
}
