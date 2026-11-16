// RASTATIME 2026-11-16 - Settings -> Track/Show Types: the show type list
// (ARCHITECTURE 23.120).  The panel is server-rendered
// (tracktype/showtypes.phtml); every save / delete answers the re-rendered
// panel, which replaces #showtype_panel.  Delegated handlers, because a
// track type save replaces the whole #content.

function rtShowtypeTips() {
  $("#showtype_panel")
    .find(".help_icon[data-rt-tip]")
    .each(function () {
      if ($(this).data("rt-tip-done")) {
        return;
      }
      $(this).data("rt-tip-done", true);
      $(this).rtTooltip({
        content: { text: $("<div>").text($(this).attr("data-rt-tip")).html() },
        placement: "right",
        interactive: true,
      });
    });
}

function rtShowtypeReplace(html) {
  $("#showtype_panel").replaceWith(html);
  rtShowtypeTips();
}

function rtShowtypeForm(row) {
  var $form = $("#showtype_form");
  $form.find(".showtype-errors").hide().empty();
  $("#showtype_id").val(row ? row.data("id") : "");
  $("#showtype_code").val(row ? row.data("code") : "");
  $("#showtype_name").val(row ? row.data("name") : "");
  $("#showtype_repeat").prop("checked", row ? String(row.data("repeat")) === "1" : false);
  $("#showtype_order").val(row ? row.data("order") : "");
  $form.show();
  $("#showtype_name").trigger("focus");
}

$(document).on("click", "#add_showtype_button", function () {
  rtShowtypeForm(null);
});

$(document).on("click", "#showtypes_table .showtype-edit", function (e) {
  e.preventDefault();
  rtShowtypeForm($(this).closest("tr"));
});

$(document).on("click", "#showtype_cancel", function () {
  $("#showtype_form").hide();
});

$(document).on("click", "#showtype_save", function () {
  var $btn = $(this).prop("disabled", true);
  $.post(
    baseUrl + "Tracktype/save-showtype/format/json",
    {
      id: $("#showtype_id").val(),
      code: $("#showtype_code").val(),
      type_name: $("#showtype_name").val(),
      counts_as_repeat: $("#showtype_repeat").prop("checked") ? "1" : "0",
      sort_order: $("#showtype_order").val(),
    },
    function (json) {
      if (json && json.ok) {
        rtShowtypeReplace(json.html);
        return;
      }
      var $err = $("#showtype_form .showtype-errors").empty();
      $.each((json && json.errors) || [], function (_, msg) {
        $err.append($("<div>").text(msg));
      });
      $err.show();
    },
    "json",
  ).always(function () {
    $btn.prop("disabled", false);
  });
});

$(document).on("click", "#showtypes_table .showtype-delete", function (e) {
  e.preventDefault();
  var $row = $(this).closest("tr");
  var shows = parseInt($row.data("shows"), 10) || 0;
  var question =
    shows > 0
      ? $.i18n._("Delete this show type? The shows using it keep no show type.")
      : $.i18n._("Delete this show type?");
  if (!confirm(question)) {
    return;
  }
  $.post(
    baseUrl + "Tracktype/remove-showtype/format/json",
    { id: $row.data("id") },
    function (json) {
      if (json && json.ok) {
        rtShowtypeReplace(json.html);
      }
    },
    "json",
  );
});

$(document).ready(rtShowtypeTips);
