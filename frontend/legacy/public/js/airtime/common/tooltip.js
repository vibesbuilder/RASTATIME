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

  // Map a qtip `at` anchor to a Floating UI placement (vertical wins for
  // corners like "bottom left"). Only the side matters for our tooltips.
  function mapPlacement(at) {
    at = (at || "").toLowerCase();
    if (at.indexOf("bottom") >= 0) {
      return "bottom";
    }
    if (at.indexOf("top") >= 0) {
      return "top";
    }
    if (at.indexOf("right") >= 0) {
      return "right";
    }
    if (at.indexOf("left") >= 0) {
      return "left";
    }
    return "right";
  }

  // Drop the qtip default theme tokens, keep any custom class (file-md-long, …).
  function stripQtipClasses(classes) {
    return (classes || "")
      .split(/\s+/)
      .filter(function (c) {
        return c && c.indexOf("ui-tooltip") !== 0;
      })
      .join(" ");
  }

  // Accept both the clean rtTooltip shape and the legacy qtip2 option shape, so
  // the migration is just `.qtip(` -> `.rtTooltip(` at the call sites.
  function normalizeOptions(o) {
    o = o || {};
    var out = {
      content: "",
      placement: "right",
      trigger: o.trigger || "hover",
      interactive: false,
      delay: o.delay != null ? o.delay : null,
      extraClass: "",
      title: o.title || "",
      closeButton: !!o.closeButton,
      dismissable: !!o.dismissable,
    };

    // content: string | function | { text } | { text, title: { text, button } }
    var content = o.content;
    if (content && typeof content === "object") {
      if (content.title) {
        out.title =
          typeof content.title === "object" ? content.title.text : content.title;
        if (content.title.button) {
          out.closeButton = true;
        }
      }
      if (content.text !== undefined) {
        content = content.text;
      }
    }
    out.content = content;

    // placement: explicit, else derived from qtip position.at (which some old
    // call sites nest inside style.position)
    if (o.placement) {
      out.placement = o.placement;
    } else if (o.position && (o.position.at || o.position.my)) {
      out.placement = mapPlacement(o.position.at);
    } else if (o.style && o.style.position && o.style.position.at) {
      out.placement = mapPlacement(o.style.position.at);
    }

    // interactive: explicit, else qtip hide.fixed
    if (o.interactive !== undefined) {
      out.interactive = !!o.interactive;
    } else if (o.hide && o.hide.fixed) {
      out.interactive = true;
    }

    // extraClass: explicit, else the non-theme tokens of qtip style.classes
    if (o.extraClass) {
      out.extraClass = o.extraClass;
    } else if (o.style && o.style.classes) {
      out.extraClass = stripQtipClasses(o.style.classes);
    }

    // dismissable: explicit, else qtip hide.event "unfocus"
    if (!out.dismissable && o.hide && o.hide.event === "unfocus") {
      out.dismissable = true;
    }

    // qtip light theme (style.name "light") -> the .rt-light variant
    if (o.style && o.style.name === "light") {
      out.extraClass = (out.extraClass + " rt-light").trim();
    }

    // a dismissable tooltip stays open (so you can click it) until an outside
    // click / Esc / close button — it must be interactive.
    if (out.dismissable) {
      out.interactive = true;
    }

    // qtip show.ready -> show immediately after init (used by click-initialised
    // tooltips such as the library track-type label)
    out.showOnInit = !!(o.show && o.show.ready);
    // qtip overwrite:false -> don't re-initialise an element that already has one
    out.overwrite = o.overwrite !== false;

    return out;
  }

  $.fn.rtTooltip = function (options) {
    var opts = normalizeOptions(options);
    var hideDelay =
      opts.delay != null ? opts.delay : opts.interactive ? 500 : 100;
    var FUI = window.FloatingUIDOM;

    return this.each(function () {
      var ref = this;
      if (!opts.overwrite && $(ref).data("rtTooltip")) {
        // already initialised on this element; just (re)show if requested
        if (opts.showOnInit) {
          $(ref).data("rtTooltip").show();
        }
        return;
      }
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
        $(ref).on("mouseenter focus", show);
        // dismissable tooltips stay open until an outside click / Esc / close
        // button; everything else hides when the pointer/focus leaves.
        if (!opts.dismissable) {
          $(ref).on("mouseleave blur", scheduleHide);
        }
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

      if (opts.showOnInit) {
        show();
      }
    });
  };

  /**
   * RASTATIME 2026-09-28 - turn Zend "description" paragraphs of a form into
   * help-icon tooltips (the /preference/stream-setting look: an empty
   * <span class="help_icon"> + rtTooltip).  The text is already translated
   * server-side; it is HTML-escaped because rtTooltip renders HTML.
   *
   *   $.rtDescriptionTooltips(root, {
   *     where: "field" | "label",   // icon after the input (dd) or after the
   *                                 // label text (dt); default "field"
   *     only: ["elementId", ...],   // limit to these Zend element ids
   *   });
   *
   * Every converted dd gets the class "with-help-icon" for page CSS.
   */
  $.rtDescriptionTooltips = function (root, options) {
    var opts = $.extend({ where: "field", only: null }, options || {});
    $(root)
      .find("dd")
      .each(function () {
        var dd = $(this);
        var desc = dd.children("p.description").first();
        if (!desc.length) {
          return;
        }
        var id = (dd.attr("id") || "").replace(/-element$/, "");
        if (opts.only && $.inArray(id, opts.only) === -1) {
          return;
        }
        var text = $.trim(desc.text());
        desc.remove();
        if (!text) {
          return;
        }
        var icon = $('<span class="help_icon"></span>');
        dd.addClass("with-help-icon");
        var dt = dd.prev("dt");
        if (opts.where === "label" && dt.length) {
          var label = dt.find("label").first();
          (label.length ? label : dt).after(icon);
        } else {
          dd.append(icon);
        }
        icon.rtTooltip({
          content: { text: $("<div>").text(text).html() },
          placement: "right",
          interactive: true,
        });
      });
  };
})(jQuery);
