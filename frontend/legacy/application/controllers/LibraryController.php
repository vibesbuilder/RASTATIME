<?php

class LibraryController extends Zend_Controller_Action
{
    /**
     * RASTATIME 2026-05-14 — Base URL for the Django REST API.  Used by
     * the Library deleteAction() so that ``linein`` items (which are
     * persisted in the new ``rastatime_linein`` table, not in any of the
     * Propel-mapped legacy tables) can be removed through their own
     * DELETE endpoint.  Mirrors :const:`LineinController::API_BASE`.
     */
    private const RASTATIME_API_BASE = 'http://localhost:8765/';

    public function init()
    {
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('contents-feed', 'json')
            ->addActionContext('delete', 'json')
            ->addActionContext('duplicate', 'json')
            ->addActionContext('duplicate-block', 'json')
            ->addActionContext('delete-group', 'json')
            ->addActionContext('context-menu', 'json')
            ->addActionContext('get-file-metadata', 'html')
            ->addActionContext('set-num-entries', 'json')
            ->addActionContext('edit-file-md', 'json')
            ->addActionContext('publish-dialog', 'html')
            ->addActionContext('redetect-cue-points', 'json')
            ->initContext();
    }

    public function indexAction()
    {
        $this->_redirect('showbuilder');
    }

    protected function playlistNotFound($p_type)
    {
        $this->view->error = sprintf(_('%s not found'), $p_type);

        Logging::info("{$p_type} not found");
        Application_Model_Library::changePlaylist(null, $p_type);
        $this->createFullResponse(null);
    }

    protected function playlistUnknownError($e)
    {
        $this->view->error = _('Something went wrong.');
        Logging::info($e->getMessage());
    }

    protected function createFullResponse($obj = null, $isJson = false)
    {
        $isBlock = false;
        $viewPath = 'playlist/playlist.phtml';
        if ($obj instanceof Application_Model_Block) {
            $isBlock = true;
            $viewPath = 'playlist/smart-block.phtml';
        }

        if (isset($obj)) {
            $formatter = new LengthFormatter($obj->getLength());
            $this->view->length = $formatter->format();

            if ($isBlock) {
                $form = new Application_Form_SmartBlockCriteria();
                $form->removeDecorator('DtDdWrapper');
                $form->startForm($obj->getId());

                $this->view->form = $form;
                $this->view->obj = $obj;
                $this->view->id = $obj->getId();
                if ($isJson) {
                    return $this->view->render($viewPath);
                }
                $this->view->html = $this->view->render($viewPath);
            } else {
                $this->view->obj = $obj;
                $this->view->id = $obj->getId();
                $this->view->html = $this->view->render($viewPath);
                unset($this->view->obj);
            }
        } else {
            $this->view->html = $this->view->render($viewPath);
        }
    }

    public function contextMenuAction()
    {
        $baseUrl = Config::getBasePath();
        $id = $this->_getParam('id');
        $type = $this->_getParam('type');
        // playlist||timeline
        $screen = $this->_getParam('screen');

        $menu = [];

        $userInfo = Zend_Auth::getInstance()->getStorage()->read();
        $user = new Application_Model_User($userInfo->id);

        // Open a jPlayer window and play the audio clip.
        $menu['play'] = ['name' => _('Preview'), 'icon' => 'play', 'disabled' => false];

        $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);

        $obj_sess = new Zend_Session_Namespace(UI_PLAYLISTCONTROLLER_OBJ_SESSNAME);

        if ($type === 'audioclip') {
            $file = Application_Model_StoredFile::RecallById($id);

            $menu['play']['mime'] = $file->getPropelOrm()->getDbMime();

            if (isset($obj_sess->id) && $screen == 'playlist') {
                // if the user is not admin or pm, check the creator and see if this person owns the playlist or Block
                if ($obj_sess->type == 'playlist') {
                    $obj = new Application_Model_Playlist($obj_sess->id);
                } elseif ($obj_sess->type == 'block') {
                    $obj = new Application_Model_Block($obj_sess->id);
                }
                if ($isAdminOrPM || $obj->getCreatorId() == $user->getId()) {
                    if ($obj_sess->type === 'playlist') {
                        $menu['pl_add'] = ['name' => _('Add to Playlist'), 'icon' => 'add-playlist', 'icon' => 'copy'];
                    } elseif ($obj_sess->type === 'block' && $obj->isStatic()) {
                        $menu['pl_add'] = ['name' => _('Add to Smart Block'), 'icon' => 'add-playlist', 'icon' => 'copy'];
                    }
                }
            }
            if ($isAdminOrPM || $file->getFileOwnerId() == $user->getId()) {
                $menu['del'] = ['name' => _('Delete'), 'icon' => 'delete', 'url' => $baseUrl . 'library/delete'];
                $menu['edit'] = ['name' => _('Edit...'), 'icon' => 'edit', 'url' => $baseUrl . "library/edit-file-md/id/{$id}"];
                // RASTATIME 2026-05-18 — Publish menu item re-enabled
                // after the PodcastEpisodeService::publish NOT-NULL
                // fix (see CHANGELOG).  Upstream had disabled it
                // following libretime#1320; that root cause does not
                // apply to RASTATIME's standalone station-podcast
                // pipeline (no SoundCloud, no Celery), so the menu
                // entry is safe to expose.
                $menu['publish'] = ['name' => _('Publish...'), 'icon' => 'edit', 'url' => $baseUrl . "library/publish/id/{$id}"];
            }

            $url = $baseUrl . "api/get-media/file/{$id}/download/true";
            $menu['download'] = ['name' => _('Download'), 'icon' => 'download', 'url' => $url];
        } elseif ($type === 'playlist' || $type === 'block') {
            if ($type === 'playlist') {
                $obj = new Application_Model_Playlist($id);
                $menu['duplicate'] = ['name' => _('Duplicate Playlist'), 'icon' => 'edit', 'url' => $baseUrl . 'library/duplicate'];
            } elseif ($type === 'block') {
                $obj = new Application_Model_Block($id);
                $menu['duplicate'] = ['name' => _('Duplicate Smartblock'), 'icon' => 'edit', 'url' => $baseUrl . 'library/duplicate-block'];
                if (!$obj->isStatic()) {
                    unset($menu['play']);
                }
                if (($isAdminOrPM || $obj->getCreatorId() == $user->getId()) && $screen == 'playlist') {
                    if ($obj_sess->type === 'playlist') {
                        $menu['pl_add'] = ['name' => _('Add to Playlist'), 'icon' => 'add-playlist', 'icon' => 'copy'];
                    }
                }
            }

            if ($obj_sess->id !== $id && $screen == 'playlist') {
                if ($isAdminOrPM || $obj->getCreatorId() == $user->getId()) {
                    $menu['edit'] = ['name' => _('Edit...'), 'icon' => 'edit'];
                }
            }

            if ($isAdminOrPM || $obj->getCreatorId() == $user->getId()) {
                $menu['del'] = ['name' => _('Delete'), 'icon' => 'delete', 'url' => $baseUrl . 'library/delete'];
            }
        } elseif ($type == 'stream') {
            $webstream = CcWebstreamQuery::create()->findPK($id);
            $obj = new Application_Model_Webstream($webstream);

            $menu['play']['mime'] = $webstream->getDbMime();

            if (isset($obj_sess->id) && $screen == 'playlist') {
                if ($isAdminOrPM || $obj->getCreatorId() == $user->getId()) {
                    if ($obj_sess->type === 'playlist') {
                        $menu['pl_add'] = ['name' => _('Add to Playlist'), 'icon' => 'add-playlist', 'icon' => 'copy'];
                    }
                }
            }
            if ($isAdminOrPM || $obj->getCreatorId() == $user->getId()) {
                if ($screen == 'playlist') {
                    $menu['edit'] = ['name' => _('Edit...'), 'icon' => 'edit', 'url' => $baseUrl . "library/edit-file-md/id/{$id}"];
                }
                $menu['del'] = ['name' => _('Delete'), 'icon' => 'delete', 'url' => $baseUrl . 'library/delete'];
            }
        } elseif ($type == 'linein') {
            // RASTATIME 2026-05-15 — Line-In rows have no Preview entry.
            //
            // Earlier this branch installed a permanently-disabled
            // "Preview (coming in Phase B)" placeholder to signal a
            // planned feature.  Operator product-decision: don't offer
            // Preview for Line-In at all (a meaningful preview would
            // need a per-row Preview-on-Demand FFmpeg-capture mechanism;
            // not worth the complexity vs. the rare "is my mic plugged
            // in?" use-case).  ``unset`` removes the default play entry
            // that was installed at the top of this method.
            unset($menu['play']);

            if ($isAdminOrPM) {
                $menu['edit'] = ['name' => _('Edit...'), 'icon' => 'edit'];
                $menu['del']  = ['name' => _('Delete'), 'icon' => 'delete', 'url' => $baseUrl . 'library/delete'];
            }
        }

        if (empty($menu)) {
            $menu['noaction'] = ['name' => _('No action available')];
        }

        $this->view->items = $menu;
    }

    public function deleteAction()
    {
        // array containing id and type of media to delete.
        $mediaItems = $this->_getParam('media', null);

        $user = Application_Model_User::getCurrentUser();
        // $isAdminOrPM = $user->isUserType(array(UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER));

        $files = [];
        $playlists = [];
        $blocks = [];
        $streams = [];
        // RASTATIME 2026-05-14 — Line-In rows live in rastatime_linein
        // (managed by the Django API), not in any Propel-mapped legacy
        // table.  Collected here and deleted in a separate loop below
        // via DELETE /api/v2/audio/linein/<id>.  Without this branch the
        // Library dashboard's "Delete" button (and the row context menu's
        // "Delete" entry) silently failed for Line-In items — the type
        // simply fell through the foreach with no error and no API call.
        $lineins = [];

        $message = null;
        $noPermissionMsg = _("You don't have permission to delete selected items.");

        foreach ($mediaItems as $media) {
            if ($media['type'] === 'audioclip') {
                $files[] = intval($media['id']);
            } elseif ($media['type'] === 'playlist') {
                $playlists[] = intval($media['id']);
            } elseif ($media['type'] === 'block') {
                $blocks[] = intval($media['id']);
            } elseif ($media['type'] === 'stream') {
                $streams[] = intval($media['id']);
            } elseif ($media['type'] === 'linein') {
                $lineins[] = intval($media['id']);
            }
        }

        try {
            Application_Model_Playlist::deletePlaylists($playlists, $user->getId());
        } catch (PlaylistNoPermissionException $e) {
            $message = $noPermissionMsg;
        }

        try {
            Application_Model_Block::deleteBlocks($blocks, $user->getId());
        } catch (BlockNoPermissionException $e) {
            $message = $noPermissionMsg;
        } catch (Exception $e) {
            // TODO: warn user that not all blocks could be deleted.
        }

        try {
            Application_Model_Webstream::deleteStreams($streams, $user->getId());
        } catch (WebstreamNoPermissionException $e) {
            $message = $noPermissionMsg;
        } catch (Exception $e) {
            // TODO: warn user that not all streams could be deleted.
            Logging::info($e);
        }

        foreach ($files as $id) {
            $file = Application_Model_StoredFile::RecallById($id);
            if (isset($file)) {
                try {
                    $res = $file->delete();
                } catch (FileNoPermissionException $e) {
                    $message = $noPermissionMsg;
                } catch (DeleteScheduledFileException $e) {
                    $message = _('Could not delete file because it is scheduled in the future.');
                } catch (Exception $e) {
                    // could throw a scheduled in future exception.
                    $message = _('Could not delete file(s).');
                    Logging::info($message . ': ' . $e->getMessage());
                }
            }
        }

        // RASTATIME 2026-05-14 — Line-In deletion via the Django API.
        // The /api/v2/audio/linein/<id> endpoint accepts either the
        // domain UUID or the numeric DB pk; we send the pk because
        // that's what the Library row carries.  Returns 204 on success,
        // 404 if already gone, anything else gets logged and surfaced
        // as a generic delete-failed message to the operator.
        foreach ($lineins as $id) {
            $url = self::RASTATIME_API_BASE . 'api/v2/audio/linein/' . $id;
            $curl = curl_init($url);
            curl_setopt_array($curl, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CUSTOMREQUEST  => 'DELETE',
                CURLOPT_TIMEOUT        => 5,
            ]);
            $body   = curl_exec($curl);
            $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
            $err    = curl_error($curl);
            curl_close($curl);

            if ($status !== 204 && $status !== 404) {
                $message = _('Could not delete some Line-In sources.');
                Logging::info(sprintf(
                    'linein delete failed: pk=%d status=%d body=%s err=%s',
                    $id, $status, (string) $body, $err
                ));
            }
        }

        if (isset($message)) {
            $this->view->message = $message;
        }
    }

    /**
     * RASTATIME 2026-09-30 - library toolbar "Cue Points": detect the cue
     * points of the selected files from their audio (ffmpeg silencedetect,
     * the analyzer's parameters), store them, and copy them into the rows
     * of the upcoming shows, which are laid out again.  Files longer than
     * Application_Model_CuePoints::DETECT_MAX_SECONDS are skipped (the
     * action is meant for jingles; a full decode of an hour is slow).
     */
    /**
     * RASTATIME 2026-10-08 - bulk metadata editor (operator request).
     * GET  library/bulk-edit-file-md?count=N  -> the dialog body
     * POST library/bulk-edit-file-md {ids[], data[]} -> applies every
     * filled field to every selected track the user may edit (owner, or
     * admin / program manager), database only like the single editor.
     */
    public function bulkEditFileMdAction()
    {
        $request = $this->getRequest();
        $user = Application_Model_User::getCurrentUser();
        $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);
        $form = new Application_Form_BulkEditAudioMD();
        $form->startForm();

        if (!$request->isPost()) {
            $this->view->layout()->disableLayout();
            $this->view->count = (int) $this->_getParam('count', 0);
            $this->view->form = $form;
            $this->_helper->viewRenderer->setScriptAction('bulk-edit-file-md');

            return;
        }

        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);

        $values = [];
        foreach ((array) $this->_getParam('data', []) as $pair) {
            if (isset($pair['name'])) {
                $values[$pair['name']] = trim((string) ($pair['value'] ?? ''));
            }
        }
        // only the filled fields travel on
        $changes = [];
        foreach (Application_Form_BulkEditAudioMD::fieldOrder() as $name) {
            if (isset($values[$name]) && $values[$name] !== '') {
                $changes[$name] = $values[$name];
            }
        }
        if (empty($changes)) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'nothing-to-change']);

            return;
        }
        // the sanitiser turns any year into an integer ("abc" -> 0): refuse
        // what is not a year before it gets the chance
        if (isset($changes['year']) && !preg_match('/^\d{4}(-\d{2}(-\d{2})?)?$/', $changes['year'])) {
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'invalid', 'messages' => ['year' => ['not a year']]]);

            return;
        }
        FileDataHelper::sanitizeData($changes);
        if (!$form->isValid($changes)) {
            Logging::warn('bulkEditFileMdAction: form INVALID, NOT saving. messages=' . json_encode($form->getMessages()));
            $this->_helper->json->sendJson(['ok' => false, 'error' => 'invalid', 'messages' => $form->getMessages()]);

            return;
        }
        $changes = array_intersect_key($form->getValues(), $changes);

        $updated = 0;
        $denied = 0;
        $missing = 0;
        foreach ((array) $this->_getParam('ids', []) as $id) {
            $file = Application_Model_StoredFile::RecallById((int) $id);
            if (!$file) {
                ++$missing;

                continue;
            }
            if (!$isAdminOrPM && $file->getFileOwnerId() != $user->getId()) {
                ++$denied;

                continue;
            }
            foreach ($changes as $name => $value) {
                $file->setDbColMetadataValue($name, $value);
            }
            ++$updated;
        }
        Logging::info(sprintf(
            'bulk-edit: user %s set %s on %d track(s) (%d denied, %d missing)',
            $user->getLogin(), implode(',', array_keys($changes)), $updated, $denied, $missing
        ));
        $this->_helper->json->sendJson(['ok' => true, 'updated' => $updated, 'denied' => $denied, 'missing' => $missing, 'fields' => array_keys($changes)]);
    }

    public function redetectCuePointsAction()
    {
        $mediaItems = $this->_getParam('media', null);
        $user = Application_Model_User::getCurrentUser();
        $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);

        $measured = 0;
        $changed = 0;
        $skipped = [];
        $denied = 0;
        $instances = [];
        $con = Propel::getConnection(CcFilesPeer::DATABASE_NAME);
        $update = $con->prepare('UPDATE cc_files SET cuein = :cuein, cueout = :cueout, mtime = :mtime WHERE id = :id');
        $started = microtime(true);
        foreach ((array) $mediaItems as $media) {
            if (!isset($media['type']) || $media['type'] !== 'audioclip') {
                continue;
            }
            $id = (int) $media['id'];
            $file = Application_Model_StoredFile::RecallById($id);
            if (!$file) {
                continue;
            }
            if (!$isAdminOrPM && $file->getFileOwnerId() != $user->getId()) {
                ++$denied;

                continue;
            }
            $orm = $file->getPropelOrm();
            $title = $orm->getDbTrackTitle() ?: ('#' . $id);
            $length = Application_Common_DateHelper::playlistTimeToSeconds((string) $orm->getDbLength());
            if ($length > Application_Model_CuePoints::DETECT_MAX_SECONDS) {
                $skipped[] = $title;

                continue;
            }
            $path = $orm->getAbsoluteFilePath();
            if (!is_file($path)) {
                $skipped[] = $title;

                continue;
            }
            $cues = Application_Model_CuePoints::detect($path, $length);
            if ($cues === null) {
                $skipped[] = $title;

                continue;
            }
            ++$measured;
            $before = [
                Application_Common_DateHelper::playlistTimeToSeconds((string) $orm->getDbCuein()),
                Application_Common_DateHelper::playlistTimeToSeconds((string) $orm->getDbCueout()),
            ];
            if (abs($cues[0] - $before[0]) < 0.005 && abs($cues[1] - $before[1]) < 0.005) {
                continue;
            }
            $update->bindValue(':cuein', Application_Model_CuePoints::formatSeconds($cues[0]));
            $update->bindValue(':cueout', Application_Model_CuePoints::formatSeconds($cues[1]));
            $update->bindValue(':mtime', gmdate('Y-m-d H:i:s'));
            $update->bindValue(':id', $id, PDO::PARAM_INT);
            $update->execute();
            ++$changed;
            Logging::info(sprintf(
                'cue points re-detected for file %d (%s): %.3f-%.3f -> %.3f-%.3f',
                $id, $title, $before[0], $before[1], $cues[0], $cues[1]
            ));
            foreach (Application_Model_CuePoints::applyToFutureRows($id, $con) as $instanceId) {
                $instances[$instanceId] = $instanceId;
            }
        }
        CcFilesPeer::clearInstancePool();
        $relaid = Application_Model_CuePoints::relayoutInstances(array_values($instances));
        Logging::info(sprintf(
            'redetect-cue-points: %d measured, %d changed, %d skipped, %d instance(s) laid out again, %.1f s',
            $measured, $changed, count($skipped), $relaid, microtime(true) - $started
        ));

        $parts = [sprintf(_('%1$s file(s) measured, %2$s changed.'), $measured, $changed)];
        if ($relaid) {
            $parts[] = sprintf(_('%s upcoming show(s) follow the new cue points.'), $relaid);
        }
        if ($skipped) {
            $parts[] = sprintf(_('Skipped (longer than %1$s minutes or not readable): %2$s'),
                (int) (Application_Model_CuePoints::DETECT_MAX_SECONDS / 60), implode(', ', array_slice($skipped, 0, 10))
                . (count($skipped) > 10 ? ' …' : ''));
        }
        if ($denied) {
            $parts[] = _("You don't have permission to change some of the selected files.");
        }
        $this->view->measured = $measured;
        $this->view->changed = $changed;
        $this->view->skipped = count($skipped);
        $this->view->message = implode(' ', $parts);
    }

    // duplicate playlist
    public function duplicateAction()
    {
        $params = $this->getRequest()->getParams();
        $id = $params['id'];
        Logging::info($params);

        $originalPl = new Application_Model_Playlist($id);
        $newPl = new Application_Model_Playlist();

        $contents = $originalPl->getContents();
        foreach ($contents as &$c) {
            if ($c['type'] == '0') {
                $c[1] = 'audioclip';
            } elseif ($c['type'] == '2') {
                $c[1] = 'block';
            } elseif ($c['type'] == '1') {
                $c[1] = 'stream';
            }
            $c[0] = $c['item_id'];
        }

        $newPl->addAudioClips($contents, null, 'before');

        $newPl->setCreator(Application_Model_User::getCurrentUser()->getId());
        $newPl->setDescription($originalPl->getDescription());

        [$plFadeIn] = $originalPl->getFadeInfo(0);
        [, $plFadeOut] = $originalPl->getFadeInfo($originalPl->getSize() - 1);

        $newPl->setfades($plFadeIn, $plFadeOut);
        $newPl->setName(sprintf(_('Copy of %s'), $originalPl->getName()));
    }

    // duplicate smartblock
    public function duplicateBlockAction()
    {
        Logging::info('duplicate smartblock functionality not yet implemented');
        $params = $this->getRequest()->getParams();
        $id = $params['id'];
        Logging::info($params);

        $originalBl = new Application_Model_Block($id);
        $newBl = new Application_Model_Block();
        $newBl->setCreator(Application_Model_User::getCurrentUser()->getId());
        $newBl->setDescription($originalBl->getDescription());
        if ($originalBl->isStatic()) {
            $newBl->saveType('static');
        } else {
            $newBl->saveType('dynamic');
        }
        // the issue here is that the format that getCriteria provides is different from the format the saveCriteria
        // expects due to the useage of startForm. So we either need to write new code that simply copies the database
        // or figure out a way to instantiate a form inside of here and save it without modifying it.
        // $newBlForm = new Application_Form_SmartBlockCriteria;
        // $newBlForm->startForm($id);
        $criteria = CcBlockcriteriaQuery::create()->orderByDbCriteria()->findByDbBlockId($id);
        foreach ($criteria as &$c) {
            $row = new CcBlockcriteria();
            $row->setDbCriteria($c->getDbCriteria());
            $row->setDbModifier($c->getDbModifier());
            $row->setDbValue($c->getDbValue());
            $row->setDbExtra($c->getDbExtra());
            $row->setDbBlockId($newBl->getId());
            $row->save();
        }
        $newBl->setName(sprintf(_('Copy of %s'), $originalBl->getName()));
    }

    public function contentsFeedAction()
    {
        $params = $this->getRequest()->getParams();

        // terrible name for the method below. it does not only search files.
        $r = Application_Model_StoredFile::searchLibraryFiles($params);

        $this->view->sEcho = $r['sEcho'];
        $this->view->iTotalDisplayRecords = $r['iTotalDisplayRecords'];
        $this->view->iTotalRecords = $r['iTotalRecords'];
        $this->view->files = SecurityHelper::htmlescape_recursive($r['aaData']);
    }

    public function editFileMdAction()
    {
        $user = Application_Model_User::getCurrentUser();
        $isAdminOrPM = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN, UTYPE_PROGRAM_MANAGER]);
        $isAdmin = $user->isUserType([UTYPE_SUPERADMIN, UTYPE_ADMIN]);

        $request = $this->getRequest();

        $file_id = $this->_getParam('id', null);
        $file = Application_Model_StoredFile::RecallById($file_id);

        $form = new Application_Form_EditAudioMD();
        $form->startForm($file_id);
        $form->populate($file->getDbColMetadata());

        $this->view->permissionDenied = false;
        if (!$isAdminOrPM && $file->getFileOwnerId() != $user->getId()) {
            $form->makeReadOnly();
            $form->removeActionButtons();
            $this->view->permissionDenied = true;
        }
        // only admins should be able to edit the owner of a file
        if (!$isAdmin) {
            $form->removeOwnerEdit();
        }

        if ($request->isPost()) {
            $js = $this->_getParam('data');
            $serialized = [];
            // need to convert from serialized jQuery array.
            foreach ($js as $j) {
                // on edit, if no artwork is set and audiofile has image, automatically add it
                if ($j['name'] == 'artwork') {
                    if ($j['value'] == null || $j['value'] == '') {
                        $serialized['artwork'] = FileDataHelper::resetArtwork($file_id);
                    }
                } elseif ($j['name'] == 'set_artwork') {
                    // Upstream had `||` here, which always evaluated true and
                    // sent an empty data-URI through to setArtwork on every
                    // save — silently overwriting the existing artwork file
                    // with an empty file.  We only want to set the artwork
                    // when the user actually chose a new image.
                    if ($j['value'] !== null && $j['value'] !== '') {
                        $serialized['artwork'] = FileDataHelper::setArtwork($file_id, $j['value']);
                    }
                } elseif ($j['name'] == 'remove_artwork') {
                    if ($j['value'] == 1) {
                        $remove_artwork = true;
                        $serialized['artwork'] = FileDataHelper::removeArtwork($file_id);
                    }
                } else {
                    $serialized[$j['name']] = $j['value'];
                }
            }

            // Sanitize any wildly incorrect metadata before it goes to be validated.
            FileDataHelper::sanitizeData($serialized);

            if ($form->isValid($serialized)) {
                $file->setDbColMetadata($serialized);
                $this->view->status = true;
            } else {
                // RASTATIME 2026-05-18 — keep a WARN-level log of which
                // form-field rejected the save.  Without this, a silent
                // validation failure (like the track_type_id=0 bug that
                // shipped before sanitizeData was fixed) just makes the
                // dialog close as if it had saved, with no breadcrumb in
                // the operator log.
                $msgs = $form->getMessages();
                Logging::warn(
                    'editFileMdAction: form INVALID, NOT saving. messages='
                    . json_encode($msgs)
                );
                $this->view->status = false;
            }
        }

        $this->view->form = $form;
        $this->view->id = $file_id;
        $this->view->title = $file->getPropelOrm()->getDbTrackTitle();
        $this->view->artist_name = $file->getPropelOrm()->getDbArtistName();
        $this->view->artwork = $file->getPropelOrm()->getDbArtwork();
        $this->view->replay_gain = $file->getPropelOrm()->getDbReplayGain();
        $this->view->cuein = $file->getPropelOrm()->getDbCuein();
        $this->view->cueout = $file->getPropelOrm()->getDbCueout();
        $this->view->format = $file->getPropelOrm()->getDbFormat();
        $this->view->bit_rate = $file->getPropelOrm()->getDbBitRate();
        $this->view->sample_rate = $file->getPropelOrm()->getDbSampleRate();
        $filePath = $file->getPropelOrm()->getDbFilepath();
        if ($isAdmin) {
            $this->view->file_name = $filePath;
        } else {
            $fileParts = explode(DIRECTORY_SEPARATOR, $filePath);
            $filename = end($fileParts);
            $this->view->file_name = $filename;
        }
        // 1000 B in KB and 1000 KB in MB and 1000 MB in GB
        $size = $file->getPropelOrm()->getFileSize();
        if ($size < 1000) {
            // Use B up to 1 KB
            $this->view->file_size = $size . ' B';
        } elseif ($size < (500 * 1000)) {
            // Use KB up to 500 KB
            $this->view->file_size = round($size / 1000, 1) . ' KB';
        } elseif ($size < (1 * 1000 * 1000 * 1000)) {
            // Use MB up to 1 GB
            $this->view->file_size = round($size / 1000 / 1000, 1) . ' MB';
        } else {
            $this->view->file_size = round($size / 1000 / 1000 / 1000, 1) . ' GB';
        }
        $this->view->html = $this->view->render('library/edit-file-md.phtml');
    }

    public function getFileMetadataAction()
    {
        $id = $this->_getParam('id');
        $type = $this->_getParam('type');

        try {
            if ($type == 'audioclip') {
                $file = Application_Model_StoredFile::RecallById($id);
                $this->view->type = $type;
                $md = $file->getMetadata();
                $storagePath = Application_Common_Storage::root();

                foreach ($md as $key => $value) {
                    if ($key == 'MDATA_KEY_DIRECTORY' && !is_null($value)) {
                        $md['MDATA_KEY_FILEPATH'] = Application_Common_OsPath::join($storagePath, $md['MDATA_KEY_FILEPATH']);
                    }
                }

                $formatter = new SamplerateFormatter($md['MDATA_KEY_SAMPLERATE']);
                $md['MDATA_KEY_SAMPLERATE'] = $formatter->format();

                $formatter = new BitrateFormatter($md['MDATA_KEY_BITRATE']);
                $md['MDATA_KEY_BITRATE'] = $formatter->format();

                $formatter = new LengthFormatter($md['MDATA_KEY_DURATION']);
                $md['MDATA_KEY_DURATION'] = $formatter->format();

                $this->view->md = $md;
            } elseif ($type == 'playlist') {
                $file = new Application_Model_Playlist($id);
                $this->view->type = $type;
                $md = $file->getAllPLMetaData();

                $formatter = new LengthFormatter($md['dcterms:extent']);
                $md['dcterms:extent'] = $formatter->format();

                $this->view->md = $md;
                $this->view->contents = $file->getContents();
            } elseif ($type == 'block') {
                $block = new Application_Model_Block($id);
                $this->view->type = $type;
                $md = $block->getAllPLMetaData();

                $formatter = new LengthFormatter($md['dcterms:extent']);
                $md['dcterms:extent'] = $formatter->format();

                $this->view->md = $md;
                if ($block->isStatic()) {
                    $this->view->blType = 'Static';
                    $this->view->contents = $block->getContents();
                } else {
                    $this->view->blType = 'Dynamic';
                    $this->view->contents = $block->getCriteria();
                }
                $this->view->block = $block;
            } elseif ($type == 'stream') {
                $webstream = CcWebstreamQuery::create()->findPK($id);
                $ws = new Application_Model_Webstream($webstream);

                $md = $ws->getMetadata();

                $this->view->md = $md;
                $this->view->type = $type;
            }
        } catch (Exception $e) {
            Logging::info($e->getMessage());
        }
    }

    public function publishDialogAction()
    {
        $this->_helper->layout->disableLayout();
        // This just spits out publish-dialog.phtml!
    }
}
