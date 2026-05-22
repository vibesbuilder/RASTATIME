<?php

/**
 * Navigation container (config/array).
 *
 * Each element in the array will be passed to
 * Zend_Navigation_Page::factory() when constructing
 * the navigation container below.
 *
 * RASTATIME 2026-05-15 - Labels are stored as plain English source
 * strings.  This file is loaded from Bootstrap.php BEFORE
 * PageLayoutInitPlugin runs configureLocalization(), so any _() call
 * here would translate against whatever locale state the Apache/fcgid
 * worker happened to carry from a previous request - on a recycled
 * worker that produces a "frozen" label in the container ("Kalender"
 * even after the operator switched the UI to English), and menu.phtml's
 * later _($page->getLabel()) call cannot reverse-translate it because
 * gettext msgid keys are always English.
 *
 * Translation happens at render time inside views/scripts/menu.phtml
 * via _($page->getLabel()).  The strings here are still referenced from
 * other .phtml templates and the .po extraction tools pick them up
 * there, so no separate xgettext marker is needed.
 */
$pages = [];
// Disable My podcasts
// See https://github.com/libretime/libretime/issues/1320
// $pages[] = array(
//     'label'      => 'My Podcast',
//     ...
// );
$pages[] = [
    'label' => 'Radio Page',
    'uri' => '/',
    'resource' => '',
    'class' => '<i class="icon-globe icon-white"></i>',
    'pages' => [],
    'visible' => false,
];
$pages[] = [
    'label' => 'Calendar',
    'module' => 'default',
    'controller' => 'schedule',
    'action' => 'index',
    'resource' => 'schedule',
    'class' => '<i class="icon-calendar icon-white"></i>',
];
$pages[] = [
    'label' => 'Widgets',
    'module' => 'default',
    'controller' => 'embeddablewidgets',
    'action' => 'player',
    'resource' => 'embeddablewidgets',
    'class' => '<i class="icon-wrench icon-white"></i>',
    'title' => 'Widgets',
    'pages' => [
        [
            'label' => 'Player',
            'module' => 'default',
            'controller' => 'embeddablewidgets',
            'action' => 'player',
        ],
        [
            'label' => 'Weekly Schedule',
            'module' => 'default',
            'controller' => 'embeddablewidgets',
            'action' => 'schedule',
        ],
        // RASTATIME 2026-05-22 — Now-Playing widget pair settings page.
        // Single submenu entry for both widgets (Current Show and
        // Current Track) since they share the same configuration
        // surface (empty-state labels, theme defaults, embed-code
        // generation).
        [
            'label' => 'Current Show/Track',
            'module' => 'default',
            'controller' => 'embeddablewidgets',
            'action' => 'current-show-track',
        ],
        // RASTATIME 2026-05-22 — Next/Latest Shows widget pair
        // settings page.  Shares the same submenu pattern as
        // Current Show/Track — preview + label customisation +
        // embed-code generation, this time keyed by show-id so
        // the operator picks WHICH show the widget should list.
        [
            'label' => 'Next/Latest Shows',
            'module' => 'default',
            'controller' => 'embeddablewidgets',
            'action' => 'next-latest-shows',
        ],
        // RASTATIME 2026-05-22 — On-Air-Today widget settings.
        // Single widget, single empty-state label, preview +
        // embed-code block.  Auto-includes the live schedule
        // (no show-picker required).
        [
            'label' => 'On Air Today',
            'module' => 'default',
            'controller' => 'embeddablewidgets',
            'action' => 'on-air-today',
        ],
    ],
];
$pages[] = [
    'label' => 'Settings',
    'action' => 'edit-user',
    'module' => 'default',
    'controller' => 'user',
    'class' => '<i class="icon-cog icon-white"></i>',
    'title' => 'Settings',
    'pages' => [
        [
            'label' => 'General',
            'module' => 'default',
            'controller' => 'preference',
            'resource' => 'preference',
        ],
        [
            'label' => 'My Profile',
            'controller' => 'user',
            'action' => 'edit-user',
        ],
        [
            'label' => 'Users',
            'module' => 'default',
            'controller' => 'user',
            'action' => 'add-user',
            'resource' => 'user',
        ], [
            'label' => 'Track Types',
            'module' => 'default',
            'controller' => 'tracktype',
            'action' => 'add-tracktype',
            'resource' => 'tracktype',
        ],
        [
            // RASTATIME 2026-05-19 — Show-Template management page
            // (Section 23.16).  CRUD for cc_show_template rows.
            'label' => 'Show Templates',
            'module' => 'default',
            'controller' => 'preference',
            'action' => 'show-templates',
            'resource' => 'preference',
        ],
        [
            // RASTATIME 2026-05-21 — Auto-DJ settings page
            // (Section 23.20).  Master switch + filler-playlist
            // selection + default show name / logo for automatic
            // gap filling.
            'label' => 'Auto DJ',
            'module' => 'default',
            'controller' => 'preference',
            'action' => 'auto-dj',
            'resource' => 'preference',
        ],
        [
            'label' => 'Streams',
            'module' => 'default',
            'controller' => 'preference',
            'action' => 'stream-setting',
            'resource' => 'preference',
        ],
        [
            // RASTATIME 2026-05-16 - Renamed from "Soundcard" to "Local Machine".
            // The page now covers both audio devices (output/input) and the
            // Local Import Folder feature (drop-folder for the analyzer).
            // The controller action stays "soundcard-setting" so existing
            // bookmarks/links keep working without a route rewrite.
            'label' => 'Local Machine',
            'module' => 'default',
            'controller' => 'preference',
            'action' => 'local-machine',
            'resource' => 'preference',
        ],
        // RASTATIME 2026-05-12 - Phase A.4 cleanup.
        // The settings-side "Line-In" navigation entry was removed.
        // All line-in management is now done in the Media Library
        // (Dashboard -> Line Inputs).  The /linein/index controller
        // route remains in place so existing /linein/* AJAX endpoints
        // used by the Library still work.
        [
            'label' => 'Status',
            'module' => 'default',
            'controller' => 'systemstatus',
            'action' => 'index',
            'resource' => 'systemstatus',
        ],
    ],
];
$pages[] = [
    'label' => 'Analytics',
    'module' => 'default',
    'controller' => 'playouthistory',
    'action' => 'index',
    'resource' => 'playouthistory',
    'class' => '<i class="icon-signal icon-white"></i>',
    'title' => 'Analytics',
    'pages' => [
        [
            'label' => 'Playout History',
            'module' => 'default',
            'controller' => 'playouthistory',
            'action' => 'index',
            'resource' => 'playouthistory',
        ],
        [
            'label' => 'History Templates',
            'module' => 'default',
            'controller' => 'playouthistorytemplate',
            'action' => 'index',
            'resource' => 'playouthistorytemplate',
        ],
        [
            'label' => 'Listener Stats',
            'module' => 'default',
            'controller' => 'listenerstat',
            'action' => 'index',
            'resource' => 'listenerstat',
        ],
        [
            'label' => 'Show Listener Stats',
            'module' => 'default',
            'controller' => 'listenerstat',
            'action' => 'show',
            'resource' => 'showlistenerstat',
        ],
    ],
];
$pages[] = [
    'label' => 'Help',
    'controller' => 'dashboard',
    'action' => 'help',
    'resource' => 'dashboard',
    'class' => '<i class="icon-question-sign icon-white"></i>',
    'title' => 'Help',
    'pages' => [
        [
            'label' => 'Getting Started',
            'module' => 'default',
            'controller' => 'dashboard',
            'action' => 'help',
            'resource' => 'dashboard',
        ],
        [
            'label' => 'User Manual',
            'uri' => USER_MANUAL_URL,
            'target' => '_blank',
        ],
        [
            'label' => 'Get Help Online',
            'uri' => LIBRETIME_DISCOURSE_URL,
            'target' => '_blank',
        ],
        [
            'label' => 'Contribute to LibreTime',
            'uri' => LIBRETIME_CONTRIBUTE_URL,
            'target' => '_blank',
        ],
        [
            'label' => 'What\'s New?',
            'uri' => LIBRETIME_WHATS_NEW_URL,
            'target' => '_blank',
        ],
    ],
];

// Create container from array
$container = new Zend_Navigation($pages);
$container->id = 'nav';

// store it in the registry:
Zend_Registry::set('Zend_Navigation', $container);
