/**
 * RASTATIME 2026-06-01 (JS-modernization stage 1)
 * ------------------------------------------------------------------
 * rtTooltip — a small vanilla tooltip helper built on Floating UI
 * (computePosition + offset/flip/shift/arrow), replacing qtip2 (EOL, 2012).
 *
 * Exposed as a jQuery plugin so the former `$(sel).qtip({...})` call sites map
 * cleanly to `$(sel).rtTooltip({...})`.  Depends on the global FloatingUIDOM
 * (js/libs/floating-ui/*) and jQuery.
 *
 * options:
 *   content      string (HTML) | function -> string     (qtip content.text)
 *   placement    Floating UI placement, default "right-start"   (qtip my/at)
 *   trigger      "hover" (default; binds mouseenter+focus) | "manual"
 *   interactive  bool — keep open while hovering the tooltip     (qtip hide.fixed)
 *   delay        hide delay ms (default 100, or 500 when interactive)
 *   extraClass   extra class(es) on the tooltip box
 *   title        optional titlebar HTML
 *   closeButton  bool — show an "x" that hides the tooltip
 *   dismissable  bool — also hide on outside click / Esc          (qtip "unfocus")
 *
 * Each matched element gets an api at $(el).data("rtTooltip"):
 *   { show, hide, setContent(content) }   (setContent updates a live tooltip).
 */
(function ($) {
  "use strict";

  function buildBox(opts) {
    var box = document.createElement("div");
    box.className =
      "rt-tooltip" +
      (opts.interactive ? " rt-interactive" : "") +
      (opts.extraClass ? " " + opts.extraClass : "");
    box.setAttribute("role", "tooltip");

    if (opts.title) {
      var titlebar = document.createElement("div");
      titlebar.className = "rt-tooltip-title";
      titlebar.innerHTML = opts.title;
      if (opts.closeButton) {
        var close = document.createElement("span");
        close.className = "rt-tooltip-close";
        close.innerHTML = "&times;";
        titlebar.appendChild(close);
      }
      box.appendChild(titlebar);
    }

    var body = document.createElement("div");
    body.className = "rt-tooltip-content";
    box.appendChild(body);

    var arrow = document.createElement("div");
    arrow.className = "rt-tooltip-arrow";
    box.appendChild(arrow);

    box._rtBody = body;
    box._rtArrow = arrow;
    return box;
  }

  function resolveContent(content) {
    // accept a plain string/function or the qtip-style { text: ... } object
    // (lets the migrated call sites keep `content: { text: ... }` unchanged)
    if (content && typeof content === "object" && content.text !== undefined) {
      content = content.text;
    }
    return typeof content === "function" ? content() : content;
  }

  function render(box, content) {
    var html = resolveContent(content);
    box._rtBody.innerHTML = html == null ? "" : html;
  }

  $.fn.rtTooltip = function (options) {
    var opts = $.extend(
      {
        content: "",
        placement: "right",
        trigger: "hover",
        interactive: false,
        delay: null,
        extraClass: "",
        title: "",
        closeButton: false,
        dismissable: false,
      },
      options,
    );
    var hideDelay =
      opts.delay != null ? opts.delay : opts.interactive ? 500 : 100;
    var FUI = window.FloatingUIDOM;

    return this.each(function () {
      var ref = this;
      var box = null,
        cleanup = null,
        hideTimer = null,
        outsideHandler = null;

      function position() {
        if (!box || !FUI) {
          return;
        }
        FUI.computePosition(ref, box, {
          placement: opts.placement,
          middleware: [
            FUI.offset(8),
            FUI.flip(),
            FUI.shift({ padding: 6 }),
            FUI.arrow({ element: box._rtArrow }),
          ],
        }).then(function (data) {
          box.style.left = data.x + "px";
          box.style.top = data.y + "px";
          var ad = data.middlewareData.arrow;
          var side = data.placement.split("-")[0];
          var staticSide = {
            top: "bottom",
            right: "left",
            bottom: "top",
            left: "right",
          }[side];
          var a = box._rtArrow.style;
          a.left = ad && ad.x != null ? ad.x + "px" : "";
          a.top = ad && ad.y != null ? ad.y + "px" : "";
          a.right = "";
          a.bottom = "";
          a[staticSide] = "-4px";
        });
      }

      function show() {
        clearTimeout(hideTimer);
        if (box) {
          return;
        }
        if (!FUI) {
          return; // Floating UI not loaded — fail safe (no tooltip)
        }
        box = buildBox(opts);
        render(box, opts.content);
        document.body.appendChild(box);

        if (opts.interactive) {
          $(box)
            .on("mouseenter", function () {
              clearTimeout(hideTimer);
            })
            .on("mouseleave", scheduleHide);
        }
        if (opts.closeButton) {
          $(box).on("click", ".rt-tooltip-close", hide);
        }
        if (opts.dismissable) {
          outsideHandler = function (e) {
            if (e.type === "keyup" && e.key !== "Escape") {
              return;
            }
            if (box && !box.contains(e.target) && e.target !== ref && !ref.contains(e.target)) {
              hide();
            }
          };
          // defer so the opening click doesn't immediately close it
          setTimeout(function () {
            $(document).on("mousedown keyup", outsideHandler);
          }, 0);
        }
        cleanup = FUI.autoUpdate(ref, box, position);
        position();
      }

      function hide() {
        clearTimeout(hideTimer);
        if (cleanup) {
          cleanup();
          cleanup = null;
        }
        if (outsideHandler) {
          $(document).off("mousedown keyup", outsideHandler);
          outsideHandler = null;
        }
        if (box && box.parentNode) {
          box.parentNode.removeChild(box);
        }
        box = null;
      }

      function scheduleHide() {
        clearTimeout(hideTimer);
        hideTimer = setTimeout(hide, hideDelay);
      }

      if (opts.trigger === "hover") {
        $(ref).on("mouseenter focus", show).on("mouseleave blur", scheduleHide);
      }
      // "manual": no auto-binding; the caller drives show/hide via the api.

      $(ref).data("rtTooltip", {
        show: show,
        hide: hide,
        setContent: function (content) {
          opts.content = content;
          if (box) {
            render(box, content);
            position();
          }
        },
      });
    });
  };
})(jQuery);
