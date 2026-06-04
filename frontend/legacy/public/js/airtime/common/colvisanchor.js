/**
 * RASTATIME 2026-06-04 (JS-modernization: ?jq3 / DataTables 1.13)
 * ------------------------------------------------------------------
 * rtColvisAnchor — anchor a DataTables Buttons "colvis" dropdown directly
 * below its trigger button instead of the centered-on-screen fallback.
 *
 * Why this exists: the library + showbuilder column-visibility dropdowns are
 * built with collectionLayout:"fixed".  Buttons' default collection is inserted
 * inline (position:absolute) next to the button, where the surrounding
 * overflow:hidden (#library_content / .sb-content) clips it to a thin strip;
 * "fixed" makes it a position:fixed panel that escapes the clip — but Buttons
 * then centers that panel on screen, which is unintuitive.  This re-anchors the
 * open panel under its button with Floating UI (bottom-end + flip + shift), the
 * same library we already use for tooltips.
 *
 * Graceful degradation: if Floating UI is missing, or anything throws, the
 * dropdown keeps the centered CSS fallback and stays fully usable.  The colvis
 * only exists on the modern (?jq3) Buttons stack, so on the legacy stack this
 * plugin is simply never called.
 *
 * Usage:  colvisButtons.container().rtColvisAnchor();
 * Depends on the global FloatingUIDOM (js/libs/floating-ui/*) and jQuery.
 */
(function ($) {
  "use strict";

  $.fn.rtColvisAnchor = function () {
    var FUI = window.FloatingUIDOM;
    if (!FUI || typeof window.MutationObserver === "undefined") {
      // Floating UI (or MutationObserver) unavailable -> keep the centered
      // fallback rather than risk a half-positioned, never-cleaned-up panel.
      return this;
    }

    return this.each(function () {
      // Delegated so the handler survives Buttons re-rendering the button node.
      $(this).on("click", ".buttons-colvis", function () {
        var button = this;

        // Buttons opens + centers the collection synchronously in this same
        // click; defer one frame, then override with a bottom-end anchor.  The
        // collection's fade-in masks the reposition, so there is no flash.
        window.requestAnimationFrame(function () {
          if (button.getAttribute("aria-expanded") !== "true") {
            return; // this click closed the dropdown -> nothing to anchor
          }
          // Buttons inserts the collection right after the button (same
          // .dt-buttons container); scope the lookup so a second colvis instance
          // on the same page can never grab this one's panel.
          var collection = button.parentNode
            ? button.parentNode.querySelector("div.dt-button-collection")
            : null;
          if (!collection) {
            return;
          }

          // The centered fallback (div.dt-button-collection.fixed) sets
          // top/left/transform with !important to beat the vendored Buttons CSS,
          // so plain inline styles would lose to it.  Inline !important still
          // wins over an author stylesheet's !important, so set it that way.
          collection.style.setProperty("transform", "none", "important");

          var reposition = function () {
            FUI.computePosition(button, collection, {
              strategy: "fixed", // matches the panel's position:fixed
              placement: "bottom-end", // under the button, right-aligned
              middleware: [
                FUI.offset(4),
                FUI.flip(), // flip above when there is no room below
                FUI.shift({ padding: 8 }), // keep it inside the viewport
              ],
            }).then(function (pos) {
              collection.style.setProperty("left", pos.x + "px", "important");
              collection.style.setProperty("top", pos.y + "px", "important");
            });
          };

          var cleanup = FUI.autoUpdate(button, collection, reposition);

          // Tear down once Buttons detaches the collection on close (after its
          // fade-out).  The observer only lives while the dropdown is open.
          var obs = new window.MutationObserver(function () {
            if (!document.body.contains(collection)) {
              cleanup();
              obs.disconnect();
            }
          });
          obs.observe(collection.parentNode || document.body, {
            childList: true,
          });
        });
      });
    });
  };
})(jQuery);
