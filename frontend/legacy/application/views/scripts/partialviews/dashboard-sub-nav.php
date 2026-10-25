<div class="media_type_selector dashboard_sub_nav" data-selection-id="<?php echo MediaType::FILE; ?>">
    <a href="<?php echo $subnavPrefix; ?>#tracks">
        <span class="selector-name"><i class='icon-music icon-white'></i><?php echo _('Tracks'); ?></span>
    </a>
</div>
<div class="media_type_selector dashboard_sub_nav" data-selection-id="<?php echo MediaType::PLAYLIST; ?>">
    <a href="<?php echo $subnavPrefix; ?>#playlists">
        <span class="selector-name"><i class='icon-list icon-white'></i><?php echo _('Playlists'); ?></span>
    </a>
</div>
<div class="media_type_selector dashboard_sub_nav" data-selection-id="<?php echo MediaType::BLOCK; ?>">
    <a href="<?php echo $subnavPrefix; ?>#smart-blocks">
        <span class="selector-name"><i class='icon-time icon-white'></i><?php echo _('Smart Blocks'); ?></span>
    </a>
</div>
<?php
// RASTATIME 2026-10-25 (role audit, operator) - DJs and guests work with
// tracks only; the webstream and Line-In tabs are for Program Managers and Admins.
$rtSubNavUser = Application_Model_User::getCurrentUser();
if ($rtSubNavUser !== null && $rtSubNavUser->isAdminOrPM()) : ?>
<div class="media_type_selector dashboard_sub_nav" data-selection-id="<?php echo MediaType::WEBSTREAM; ?>">
    <a href="<?php echo $subnavPrefix; ?>#webstreams">
        <span class="selector-name"><i class='icon-random icon-white'></i><?php echo _('Webstreams'); ?></span>
    </a>
</div>
<!-- RASTATIME 2026-05-12 — Line-In Media-Library tab.
     Sits between Webstreams and Podcasts per operator request. -->
<div class="media_type_selector dashboard_sub_nav" data-selection-id="<?php echo MediaType::LINEIN; ?>">
    <a href="<?php echo $subnavPrefix; ?>#lineins">
        <span class="selector-name"><i class='icon-volume-up icon-white'></i><?php echo _('Line Inputs'); ?></span>
    </a>
</div>
<?php endif; ?>
