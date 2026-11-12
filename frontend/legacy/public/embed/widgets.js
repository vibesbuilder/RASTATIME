/*
 * RASTATIME widgets: automatic height for the /embed/ iframes.
 *
 * Put this script once on a page that embeds RASTATIME widgets (every
 * embed code from Widgets -> ... carries it; including it several times
 * is harmless).  Each widget iframe from the same server then grows and
 * shrinks with its content instead of keeping the fixed height of its
 * height attribute, which stays the fallback for visitors without
 * JavaScript and for widgets that keep a fixed size (the player bar).
 *
 *   <iframe src="https://radio.example.org/embed/weekly-program"
 *           width="100%" height="670" style="border: 0; max-width: 670px;"
 *           scrolling="no"></iframe>
 *   <script src="https://radio.example.org/embed/widgets.js" async></script>
 *
 * Opt one iframe out with data-rt-autoheight="off".
 *
 * Only messages from the server this script was loaded from are read,
 * and only for iframes on this page that show that server's widgets.
 * The script sets nothing but the iframe height; it reads no cookies
 * and sends nothing anywhere except the visible part of each widget
 * back to that widget (so its dialogs open where the visitor looks).
 *
 * RASTATIME 2026-11-12.
 */
(function () {
    'use strict';

    var script = document.currentScript;
    if (!script) {
        var all = document.getElementsByTagName('script');
        for (var i = all.length - 1; i >= 0; i--) {
            if (/\/embed\/widgets\.js(\?|#|$)/i.test(all[i].src)) {
                script = all[i];
                break;
            }
        }
    }
    if (!script || !script.src || !window.postMessage) {
        return;
    }
    var a = document.createElement('a');
    a.href = script.src;
    var ORIGIN = a.protocol + '//' + a.host;
    // IE/old Edge add the default port to host; postMessage origins never do.
    ORIGIN = ORIGIN.replace(/:443$/, '').replace(/^(http:\/\/[^\/]+):80$/, '$1');

    var registry = window.RastatimeWidgets = window.RastatimeWidgets || {};
    if (registry[ORIGIN]) {
        return;   // already running for this server
    }
    registry[ORIGIN] = { version: 1 };

    var MIN_HEIGHT = 24;
    var MAX_HEIGHT = 30000;
    var active = [];   // iframes that report their height

    function isOurs(frame) {
        if (!frame || frame.getAttribute('data-rt-autoheight') === 'off') {
            return false;
        }
        var src = frame.getAttribute('src') || '';
        a.href = src;   // resolves relative URLs too
        var origin = (a.protocol + '//' + a.host)
            .replace(/:443$/, '').replace(/^(http:\/\/[^\/]+):80$/, '$1');
        var path = a.pathname.charAt(0) === '/' ? a.pathname : '/' + a.pathname;
        return origin === ORIGIN && /^\/embed\//i.test(path);
    }

    function hello(frame) {
        try {
            frame.contentWindow.postMessage({ rtWidget: 1, type: 'hello' }, ORIGIN);
        } catch (e) { /* not loaded yet: the widget's ready message follows */ }
    }

    function frameFor(source) {
        var frames = document.getElementsByTagName('iframe');
        for (var j = 0; j < frames.length; j++) {
            if (frames[j].contentWindow === source) {
                return frames[j];
            }
        }
        return null;
    }

    function sendViewport(frame) {
        var r = frame.getBoundingClientRect();
        var vh = window.innerHeight || document.documentElement.clientHeight || 0;
        var top = Math.max(0, -r.top);
        var bottom = Math.min(r.height, vh - r.top);
        try {
            frame.contentWindow.postMessage({
                rtWidget: 1,
                type: 'viewport',
                top: Math.round(top),
                height: Math.round(Math.max(0, bottom - top)),
                vh: Math.round(vh)
            }, ORIGIN);
        } catch (e) { /* frame removed */ }
    }

    var pending = false;
    function viewportsSoon() {
        if (pending || !active.length) { return; }
        pending = true;
        var run = function () {
            pending = false;
            for (var k = active.length - 1; k >= 0; k--) {
                if (!document.documentElement.contains(active[k])) {
                    active.splice(k, 1);
                } else {
                    sendViewport(active[k]);
                }
            }
        };
        if (window.requestAnimationFrame) {
            window.requestAnimationFrame(run);
        } else {
            window.setTimeout(run, 50);
        }
    }

    window.addEventListener('message', function (e) {
        if (e.origin !== ORIGIN) { return; }
        var data = e.data;
        if (!data || data.rtWidget !== 1) { return; }
        var frame = frameFor(e.source);
        if (!frame || !isOurs(frame)) { return; }

        if (data.type === 'ready') {
            hello(frame);
        } else if (data.type === 'height') {
            var h = Math.round(Number(data.height) || 0);
            if (h < MIN_HEIGHT) { return; }
            frame.style.height = Math.min(h, MAX_HEIGHT) + 'px';
            if (active.indexOf(frame) === -1) {
                active.push(frame);
            }
            sendViewport(frame);
        } else if (data.type === 'fixed') {
            var idx = active.indexOf(frame);
            if (idx !== -1) { active.splice(idx, 1); }
        }
    });

    window.addEventListener('scroll', viewportsSoon, { passive: true, capture: true });
    window.addEventListener('resize', viewportsSoon);

    function scan() {
        var frames = document.getElementsByTagName('iframe');
        for (var j = 0; j < frames.length; j++) {
            var frame = frames[j];
            if (!isOurs(frame) || frame.getAttribute('data-rt-widgets-seen')) {
                continue;
            }
            frame.setAttribute('data-rt-widgets-seen', '1');
            // A reload inside the frame (week navigation) starts over.
            frame.addEventListener('load', (function (f) {
                return function () { hello(f); };
            })(frame));
            hello(frame);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scan);
    } else {
        scan();
    }
})();
