/*
 * RASTATIME 2026-11-12 — self-sizing widgets, the widget side.
 *
 * Loaded by every /embed/ page.  Does nothing on its own: the widget
 * keeps the fixed height its iframe gives it, exactly as before.  Only
 * when the embedding page runs /embed/widgets.js (the loader) and that
 * script says hello, the widget switches to "as tall as its content":
 *
 *   widget -> page  {rtWidget: 1, type: 'ready'}         on load
 *   page -> widget  {rtWidget: 1, type: 'hello'}         loader found us
 *   widget -> page  {rtWidget: 1, type: 'height', height: N}
 *                                                         on every change
 *   page -> widget  {rtWidget: 1, type: 'viewport', top, height, vh}
 *                                                         on scroll/resize
 *   widget -> page  {rtWidget: 1, type: 'fixed'}         widget opts out
 *
 * In auto mode <html> carries the class "rt-autoheight"; the widget CSS
 * drops its inner scroll boxes and 100vh layouts under that class.  The
 * viewport message tells the widget which part of its frame the visitor
 * actually sees (CSS variables --rt-vp-top / --rt-vp-height) and how tall
 * the visitor's window is (--rt-parent-vh), so a dialog opens where the
 * visitor looks and the Multi-View calendar can size itself to the screen.
 *
 * A widget opts out with <body data-rt-autoheight="off"> (the player bar
 * fills the height the page gives it).
 *
 * Vanilla JS (no jQuery) — the iframe runs in isolation.
 */

(function () {
    'use strict';

    if (window.parent === window || !window.postMessage) {
        return;   // not framed: nothing to report to
    }

    var root = document.documentElement;
    var parentOrigin = null;   // origin of the page that said hello
    var lastHeight = -1;
    var lastParentVh = -1;

    function post(msg) {
        msg.rtWidget = 1;
        try {
            window.parent.postMessage(msg, parentOrigin || '*');
        } catch (e) { /* parent gone */ }
    }

    function measure() {
        // <html> is height:auto in auto mode, so its box is the content.
        return Math.ceil(root.getBoundingClientRect().height);
    }

    function report() {
        if (!parentOrigin) { return; }
        var h = measure();
        if (h !== lastHeight && h > 0) {
            lastHeight = h;
            post({ type: 'height', height: h });
        }
    }

    function optedOut() {
        return document.body
            && document.body.getAttribute('data-rt-autoheight') === 'off';
    }

    function emit(name) {
        try {
            document.dispatchEvent(new CustomEvent(name));
        } catch (e) { /* very old browser: the CSS alone still applies */ }
    }

    function start() {
        root.classList.add('rt-autoheight');
        emit('rt-autoheight');
        if (window.ResizeObserver) {
            var observer = new ResizeObserver(report);
            observer.observe(root);
            if (document.body) { observer.observe(document.body); }
        }
        // Browsers pause rendering - and with it the ResizeObserver - in a
        // cross-origin frame that is off screen, so a widget further down
        // the page would keep a stale height until it scrolls into view.
        // A cheap re-measure once a second (a layout read; nothing happens
        // when the height is unchanged) keeps it current regardless.
        window.setInterval(report, 1000);
        // Late layout changes the observer may miss (web fonts, images).
        window.addEventListener('load', report);
        report();
    }

    function onViewport(data) {
        var top = Math.max(0, Number(data.top) || 0);
        var height = Math.max(0, Number(data.height) || 0);
        var vh = Math.max(0, Number(data.vh) || 0);
        root.style.setProperty('--rt-vp-top', top + 'px');
        if (height > 0) {
            root.style.setProperty('--rt-vp-height', height + 'px');
        }
        if (vh > 0 && vh !== lastParentVh) {
            lastParentVh = vh;
            root.style.setProperty('--rt-parent-vh', vh + 'px');
            emit('rt-autoheight-resize');
        }
    }

    window.addEventListener('message', function (e) {
        // Only the page directly around this frame may switch it.
        if (e.source !== window.parent) { return; }
        var data = e.data;
        if (!data || data.rtWidget !== 1) { return; }

        if (data.type === 'hello') {
            if (optedOut()) {
                parentOrigin = e.origin;
                post({ type: 'fixed' });
                return;
            }
            var first = parentOrigin === null;
            parentOrigin = e.origin;
            if (first) {
                start();
            } else {
                // The page asked again (its loader started late): resend.
                lastHeight = -1;
                report();
            }
        } else if (data.type === 'viewport' && parentOrigin === e.origin) {
            onViewport(data);
        }
    });

    function ready() {
        post({ type: 'ready' });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ready);
    } else {
        ready();
    }
})();
