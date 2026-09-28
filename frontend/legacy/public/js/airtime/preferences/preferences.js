function showErrorSections() {
  var selector = $("[id$=-settings]");
  selector.each(function (i) {
    var el = $(this);
    var errors = el.find(".errors");
    if (errors.length > 0) {
      el.show();
      $(window).scrollTop(errors.position().top);
    }
  });
}

function setConfigureMailServerListener() {
  var configMailServer = $("#configureMailServer");
  configMailServer.click(function (event) {
    setMailServerInputReadonly();
  });

  var msRequiresAuth = $("#msRequiresAuth");
  msRequiresAuth.click(function (event) {
    setMsAuthenticationFieldsReadonly($(this));
  });
}

function setEnableSystemEmailsListener() {
  var enableSystemEmails = $("#enableSystemEmail");
  enableSystemEmails.click(function (event) {
    setSystemFromEmailReadonly();
  });
}

function setPodcastAutoSmartblockReadonly() {
  var disablePodcastAutomSmartblock = $("#podcastAutoSmartblock-0");
  var enablePodcastAutomSmartblock = $("#podcastAutoSmartblock-1");
  var podcastOverride = $("#podcastAlbumOverride-1");
  if ($(podcastOverride).is(":checked")) {
    enablePodcastAutomSmartblock.removeAttr("readonly");
  } else {
    disablePodcastAutomSmartblock.prop("checked", true);
    disablePodcastAutomSmartblock.attr("readonly", "readonly");
    enablePodcastAutomSmartblock.attr("readonly", "readonly");
  }
}

function setSystemFromEmailReadonly() {
  var enableSystemEmails = $("#enableSystemEmail");
  var systemFromEmail = $("#systemEmail");
  if ($(enableSystemEmails).is(":checked")) {
    systemFromEmail.removeAttr("readonly");
  } else {
    systemFromEmail.attr("readonly", "readonly");
  }
}

function setMailServerInputReadonly() {
  var configMailServer = $("#configureMailServer");
  var mailServer = $("#mailServer");
  var port = $("#port");
  var requiresAuthCB = $("#msRequiresAuth");

  if (configMailServer.is(":checked")) {
    mailServer.removeAttr("readonly");
    port.removeAttr("readonly");
    requiresAuthCB.parent().show();
  } else {
    mailServer.attr("readonly", "readonly");
    port.attr("readonly", "readonly");
    requiresAuthCB.parent().hide();
  }

  setMsAuthenticationFieldsReadonly(requiresAuthCB);
}

function setTuneInSettingsListener() {
  var enableTunein = $("#enable_tunein");
  enableTunein.click(function (event) {
    setTuneInSettingsReadonly();
  });
}

function setTuneInSettingsReadonly() {
  var enableTunein = $("#enable_tunein");
  var stationId = $("#tunein_station_id");
  var partnerKey = $("#tunein_partner_key");
  var partnerId = $("#tunein_partner_id");

  if (enableTunein.is(":checked")) {
    stationId.removeAttr("readonly");
    partnerKey.removeAttr("readonly");
    partnerId.removeAttr("readonly");
  } else {
    stationId.attr("readonly", "readonly");
    partnerKey.attr("readonly", "readonly");
    partnerId.attr("readonly", "readonly");
  }
}

/*
 * Enable/disable mail server authentication fields
 */
function setMsAuthenticationFieldsReadonly(ele) {
  var email = $("#email");
  var password = $("#ms_password");
  var configureMailServer = $("#configureMailServer");

  if (ele.is(":checked") && configureMailServer.is(":checked")) {
    email.removeAttr("readonly");
    password.removeAttr("readonly");
  } else if (ele.not(":checked") || configureMailServer.not(":checked")) {
    email.attr("readonly", "readonly");
    password.attr("readonly", "readonly");
  }
}

function removeLogo() {
  $.post(
    baseUrl + "preference/remove-logo",
    { csrf_token: $("#csrf").val() },
    function (json) {
      // Reload without resubmitting the form
      location.href = location.href.replace(location.hash, "");
    },
  );
}

// RASTATIME 2026-05-15 - Counterpart to removeLogo for the custom favicon.
function removeFavicon() {
  $.post(
    baseUrl + "preference/remove-favicon",
    { csrf_token: $("#csrf").val() },
    function (json) {
      location.href = location.href.replace(location.hash, "");
    },
  );
}

function deleteAllFiles() {
  var resp = confirm(
    $.i18n._("Are you sure you want to delete all the tracks in your library?"),
  );
  if (resp) {
    $.post(
      baseUrl + "preference/delete-all-files",
      { csrf_token: $("#csrf").val() },
      function (json) {
        location.reload();
      },
    );
  }
}

// RASTATIME 2026-06-08 — render the "Song-Request Pool" MultiCheckbox as a
// "Smart Blocks" dropdown styled after the Library "Columns" colvis control:
// a grey button toggling a dark panel of checkboxes.  The checkbox markup
// (names / values / submit) is only WRAPPED, never changed, so the form posts
// exactly as before; the look lives in styles.css (.rt-sbdd*).
function setupRequestablePoolDropdown() {
  var $dd = $("#requestablePoolSelect-element");
  if ($dd.length === 0 || $dd.find(".rt-sbdd-button").length > 0) {
    return;
  }
  var $panel = $('<div class="rt-sbdd-panel"></div>').append($dd.contents());
  var $btn = $('<button type="button" class="rt-sbdd-button">Smart Blocks</button>');
  var $wrap = $('<div class="rt-sbdd"></div>').append($btn, $panel);
  $dd.append($wrap);

  $btn.on("click", function (e) {
    e.stopPropagation();
    $wrap.toggleClass("open");
  });
  $(document).on("click", function (e) {
    if ($(e.target).closest(".rt-sbdd").length === 0) {
      $wrap.removeClass("open");
    }
  });
}

$(document).ready(function () {
  setupRequestablePoolDropdown();

  // RASTATIME 2026-09-28 - the long explanations under these General
  // fields become help-icon tooltips right of the label (operator wish);
  // the short notes under Station Logo / Favicon stay as text.
  $.rtDescriptionTooltips($("#general-settings, form"), {
    where: "label",
    only: [
      "stationDefaultCrossfadeDuration",
      "stationDefaultShowCrossfadeDuration",
      "trafficAlertBlockSelect",
      "showShiftFillerPlaylistSelect",
      "podcastAlbumOverride",
      "podcastAutoSmartblock",
      "thirdPartyApi",
    ],
  });
  $(document).on("click", ".collapsible-header", function () {
    $(this).next().toggle("fast");
    $(this).toggleClass("closed");
    return false;
  });

  if ($("#tunein-settings").find(".errors").length > 0) {
    $(".collapsible-content#tunein-settings").show();
  }

  /* No longer using AJAX for this form. Zend + our code makes it needlessly hard to deal with. -- Albert
    $('#pref_save').live('click', function() {
        var data = $('#pref_form').serialize();
        var url = baseUrl+'Preference/index';

        $.post(url, {format: "json", data: data}, function(json){
            $('#content').empty().append(json.html);
            setTimeout(removeSuccessMsg, 5000);
            showErrorSections();
            setMailServerInputReadonly();
            setConfigureMailServerListener();
            setEnableSystemEmailsListener();
        });
    });*/

  // when an image is uploaded, preview it to the user
  var logo = $("#stationLogo"),
    preview = $("#logo-img");
  logo.change(function (e) {
    if (this.files && this.files[0]) {
      preview.show();
      var reader = new FileReader(); // browser compatibility?
      reader.onload = function (e) {
        console.log("Reader loaded");
        preview.attr("src", e.target.result);
      };

      // check image size so we don't crash the page trying to render
      if (validateImage(this.files[0], logo)) {
        // read the image data as though it were a data URI
        reader.readAsDataURL(this.files[0]);
      } else {
        // remove the file element data
        $(this).val("").replaceWith($(this).clone(true));
        preview.hide();
      }
    } else {
      preview.hide();
    }
  });

  // RASTATIME 2026-05-15 - Same live-preview wiring for the favicon upload.
  // No size validation here (favicons are tiny by definition; the form's
  // setMaxFileSize(200000) is the only gate).
  var favicon = $("#stationFavicon"),
    faviconPreview = $("#favicon-img");
  favicon.change(function (e) {
    if (this.files && this.files[0]) {
      // Create the preview <img> if it didn't exist yet (operator hadn't
      // uploaded one before).
      if (faviconPreview.length === 0) {
        $("#Favicon-img-container").append('<img id="favicon-img" />');
        faviconPreview = $("#favicon-img");
      }
      faviconPreview.show();
      $("#favicon-remove-btn").show();
      var reader = new FileReader();
      reader.onload = function (e) {
        faviconPreview.attr("src", e.target.result);
      };
      reader.readAsDataURL(this.files[0]);
    }
  });

  if (preview.attr("src").indexOf("images/") > -1) {
    $("#logo-remove-btn").hide();
  }

  showErrorSections();

  setMailServerInputReadonly();
  setPodcastAutoSmartblockReadonly();
  setSystemFromEmailReadonly();
  setConfigureMailServerListener();
  setEnableSystemEmailsListener();
  setTuneInSettingsReadonly();
  setTuneInSettingsListener();
});
