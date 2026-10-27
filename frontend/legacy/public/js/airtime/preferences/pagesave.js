/*
 * RASTATIME 2026-10-27 - one Save per Settings page (operator rule: one
 * Save top right, the same at the bottom, saving everything on the page).
 *
 * Local Machine and Backup save each section through its own endpoint.
 * A section registers its fields and a save function returning a
 * promise (resolved when the server accepted it); markSaved() records
 * the stored state once the fields show it.  The page's Save buttons
 * (.rt-page-save) then post only the sections whose fields changed, one
 * after the other in page order.  Unchanged sections are not posted
 * again: some make the playout reconfigure itself (main output, 24/7
 * recording).  A section that was never marked saved (its values did
 * not load) is skipped.  Each section keeps writing its own status
 * message; the summary goes next to the Save buttons (.rt-page-save-msg).
 */
var RtPageSave = (function ($) {
  var sections = [];
  var texts = {
    saving: "Saving …",
    saved: "Saved.",
    nothing: "No changes to save.",
    failed: "Some sections could not be saved - see the messages there.",
  };

  function state(section) {
    return $(section.fields)
      .map(function () {
        if (this.type === "checkbox") {
          return this.checked ? "1" : "0";
        }
        var v = $(this).val();
        return v === null || v === undefined ? "" : String(v);
      })
      .get()
      .join("\u0001");
  }

  function register(name, fields, save) {
    var section = { name: name, fields: fields, save: save, saved: null };
    sections.push(section);
    return section;
  }

  function markSaved(section) {
    section.saved = state(section);
  }

  // in page order (by the first field), whatever order the scripts
  // registered them in - e.g. the Import Folder before the FTP import
  // that lands in it
  function changed() {
    return $.grep(sections, function (s) {
      return s.saved !== null && state(s) !== s.saved;
    }).sort(function (a, b) {
      var x = $(a.fields).get(0);
      var y = $(b.fields).get(0);
      if (!x || !y || x === y) {
        return 0;
      }
      return x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
    });
  }

  function message(text, ok) {
    $(".rt-page-save-msg")
      .text(text)
      .css("color", ok ? "#5cb85c" : "#d9534f");
  }

  function saveAll() {
    var todo = changed();
    if (!todo.length) {
      message(texts.nothing, true);
      return;
    }
    var failed = 0;
    $(".rt-page-save").prop("disabled", true);
    message(texts.saving, true);

    function next(i) {
      if (i >= todo.length) {
        $(".rt-page-save").prop("disabled", false);
        message(failed ? texts.failed : texts.saved, !failed);
        return;
      }
      var section = todo[i];
      var p = null;
      try {
        p = section.save();
      } catch (e) {
        p = null;
      }
      if (!p) {
        failed++;
        next(i + 1);
        return;
      }
      p.done(function () {
        markSaved(section);
      })
        .fail(function () {
          failed++;
        })
        .always(function () {
          next(i + 1);
        });
    }
    next(0);
  }

  $(document).on("click", ".rt-page-save", function () {
    saveAll();
  });

  return {
    register: register,
    markSaved: markSaved,
    saveAll: saveAll,
    setTexts: function (t) {
      $.extend(texts, t);
    },
  };
})(jQuery);
