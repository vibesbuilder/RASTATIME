<?php

$ccAcl = new Zend_Acl();

$ccAcl->addRole(new Zend_Acl_Role('G'))
    ->addRole(new Zend_Acl_Role('H'), 'G')
    ->addRole(new Zend_Acl_Role('P'), 'H')
    ->addRole(new Zend_Acl_Role('A'), 'P')
    // 'S' (Super Admin) is retired since 2026-10-25 (migration 0073 turns
    // such accounts into Admins); the role stays as a harmless alias of 'A'
    ->addRole(new Zend_Acl_Role('S'), 'A');

$ccAcl->add(new Zend_Acl_Resource('library'))
    ->add(new Zend_Acl_Resource('index'))
    ->add(new Zend_Acl_Resource('user'))
    ->add(new Zend_Acl_Resource('tracktype'))
    ->add(new Zend_Acl_Resource('error'))
    ->add(new Zend_Acl_Resource('login'))
    ->add(new Zend_Acl_Resource('playlist'))
    ->add(new Zend_Acl_Resource('plupload'))
    ->add(new Zend_Acl_Resource('schedule'))
    ->add(new Zend_Acl_Resource('api'))
    ->add(new Zend_Acl_Resource('systemstatus'))
    ->add(new Zend_Acl_Resource('dashboard'))
    ->add(new Zend_Acl_Resource('preference'))
    ->add(new Zend_Acl_Resource('importexport'))
    ->add(new Zend_Acl_Resource('showbuilder'))
    ->add(new Zend_Acl_Resource('playouthistory'))
    ->add(new Zend_Acl_Resource('playouthistorytemplate'))
    ->add(new Zend_Acl_Resource('listenerstat'))
    ->add(new Zend_Acl_Resource('showlistenerstat'))
    ->add(new Zend_Acl_Resource('usersettings'))
    ->add(new Zend_Acl_Resource('audiopreview'))
    ->add(new Zend_Acl_Resource('webstream'))
    ->add(new Zend_Acl_Resource('locale'))
    ->add(new Zend_Acl_Resource('upgrade'))
    ->add(new Zend_Acl_Resource('downgrade'))
    ->add(new Zend_Acl_Resource('rest:media'))
    ->add(new Zend_Acl_Resource('rest:show-image'))
    ->add(new Zend_Acl_Resource('rest:podcast'))
    ->add(new Zend_Acl_Resource('rest:podcast-episodes'))
    ->add(new Zend_Acl_Resource('podcast'))
    ->add(new Zend_Acl_Resource('player'))
    ->add(new Zend_Acl_Resource('render'))
    ->add(new Zend_Acl_Resource('embeddablewidgets'))
    ->add(new Zend_Acl_Resource('setup'))
    ->add(new Zend_Acl_Resource('feeds'))
    ->add(new Zend_Acl_Resource('linein'))  // T14.2 — Line-In source management
    ->add(new Zend_Acl_Resource('manual'))  // RASTATIME 2026-10-01 — in-app user manual
    ->add(new Zend_Acl_Resource('archiving'));  // RASTATIME 2026-11-03 — editorial team, participants

// Creating permissions
$ccAcl->allow('G', 'index')
    ->allow('G', 'login')
    ->allow('G', 'error')
    ->allow('G', 'user', 'edit-user')
    ->allow('G', 'showbuilder')
    ->allow('G', 'render')
    ->allow('G', 'api')
    ->allow('G', 'schedule')
    ->allow('G', 'dashboard')
    ->allow('G', 'manual')
    ->allow('G', 'audiopreview')
    ->allow('G', 'locale')
    ->allow('G', 'upgrade')
    ->allow('G', 'downgrade')
    ->allow('G', 'rest:show-image', 'get')
    ->allow('G', 'rest:media', 'get')
    ->allow('G', 'rest:podcast', 'get')
    ->allow('G', 'rest:podcast-episodes', 'get')
    ->allow('G', 'setup')
    ->allow('G', 'feeds')
    // RASTATIME 2026-10-25 (role audit R7/R8) - DJs change no show logos
    // and manage no podcasts (operator); they keep reading the podcast list.
    ->allow('H', 'rest:media')
    ->allow('H', 'rest:podcast', ['index', 'get'])
    ->allow('H', 'rest:podcast-episodes', ['index', 'get'])
    ->allow('H', 'preference', 'is-import-in-progress')
    ->allow('H', 'usersettings')
    ->allow('H', 'plupload')
    ->allow('H', 'library')
    ->allow('H', 'playlist')
    ->allow('H', 'playouthistory')
    ->allow('H', 'listenerstat')
    ->allow('H', 'showlistenerstat')
    // RASTATIME 2026-10-25 (role audit R7/R8/R10) - show logos, podcasts,
    // webstreams and Line-In sources: Program Managers and Admins (operator;
    // DJs and guests work with tracks only).
    ->allow('P', 'rest:show-image')
    ->allow('P', 'rest:podcast')
    ->allow('P', 'rest:podcast-episodes')
    ->allow('P', 'podcast')
    ->allow('P', 'archiving', ['settings', 'editors', 'participants', 'participants-csv'])  // RASTATIME 2026-11-03 — archiving
    ->allow('A', 'archiving')  // RASTATIME 2026-11-03 — CBA accounts: admins only
    ->allow('P', 'webstream')
    ->allow('P', 'linein')
    // RASTATIME 2026-10-25 (operator) - Program Managers run the Auto DJ and
    // the Show Templates page, and own the Widgets pages (hidden from Guests
    // and DJs; the public embeds live in the separate 'embed' controller)
    ->allow('P', 'preference', ['auto-dj', 'auto-dj-upload-logo', 'auto-dj-remove-logo', 'show-templates'])
    ->allow('P', 'embeddablewidgets')
    ->allow('A', 'playouthistorytemplate')
    ->allow('A', 'user')
    ->allow('A', 'tracktype')
    ->allow('A', 'systemstatus')
    ->allow('A', 'preference')
    ->allow('A', 'importexport');

$aclPlugin = new Zend_Controller_Plugin_Acl($ccAcl);

Zend_View_Helper_Navigation_HelperAbstract::setDefaultAcl($ccAcl);

$front = Zend_Controller_Front::getInstance();
$front->registerPlugin($aclPlugin);
