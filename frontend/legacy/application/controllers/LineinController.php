<?php

/**
 * T14.2 / T14.3 — Line-In source management controller.
 *
 * Provides the list view and the JSON Ajax endpoints used by the add / edit /
 * delete / enable–disable dialog introduced in T14.3.
 *
 * All mutating actions (create, update, delete) are thin pass-throughs to
 * the Python API at /api/v2/audio/linein[/<id>].  The controller only
 * enforces ACL; the Python layer owns validation and persistence.
 *
 * Access: Admin (A) and Super Admin (S) only — see ACL.php.
 */
class LineinController extends Zend_Controller_Action
{
    /**
     * Base URL of the Django REST API (Waitress on localhost:8765).
     *
     * Hardcoded for two reasons:
     *  - The legacy ``AIRTIME_BASE_URL`` constant inherited from the
     *    Airtime-era codebase is not defined anywhere in RASTATIME's
     *    boot path, so any controller that referenced it crashed
     *    with "Undefined constant" on PHP 8.x.
     *  - Direct loopback to 8765 avoids an unnecessary Apache→Django
     *    proxy roundtrip — same pattern as PodcastEpisodeService.php.
     *
     * If the API is ever moved to another host/port, change here.
     */
    private const API_BASE = 'http://localhost:8765/';

    public function init()
    {
        // Register JSON Ajax contexts so ZF renders no layout for XHR calls.
        $ajaxContext = $this->_helper->getHelper('AjaxContext');
        $ajaxContext->addActionContext('create', 'json')
                    ->addActionContext('update', 'json')
                    ->addActionContext('delete', 'json')
                    // RASTATIME 2026-05-12 — Library actions
                    // (analogous to WebstreamController).
                    ->addActionContext('new',  'json')
                    ->addActionContext('edit', 'json')
                    ->addActionContext('save', 'json')
                    ->initContext();
    }

    /**
     * RASTATIME 2026-10-25 (role audit S4) - the device list for the Line-In
     * edit dialog (spl.js), proxied from the API on localhost; the browser
     * no longer reaches /api/v2/audio/devices (internal callers only).
     */
    public function audioDevicesAction(): void
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $curl = curl_init(self::API_BASE . 'api/v2/audio/devices');
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_HTTPHEADER => ['Accept: application/json'],
        ]);
        $resp = curl_exec($curl);
        $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);
        $this->getResponse()
            ->setHttpResponseCode($status ?: 502)
            ->setHeader('Content-Type', 'application/json', true)
            ->setBody(is_string($resp) && $resp !== '' ? $resp : '{"error":"The RASTATIME API is not reachable."}');
    }

    // -------------------------------------------------------------------------
    // List view (T14.2)
    // -------------------------------------------------------------------------

    /**
     * GET /linein — redirects to the Dashboard, where the Library's
     * Line Inputs view and its dialog are the one line-in editor since
     * 2026-09-17 (before that: Settings → Local Machine section since
     * 2026-08-31; standalone page before).  Kept as a route so old
     * deep links stay functional.
     */
    public function indexAction(): void
    {
        $this->_redirect('showbuilder');
    }

    // -------------------------------------------------------------------------
    // Ajax actions (T14.3) — proxy to Python API
    // -------------------------------------------------------------------------

    /**
     * POST /linein/create — create a new line-in source.
     *
     * Expects a JSON body forwarded from the JS dialog.
     * Returns the created entry (HTTP 201 from Python, re-wrapped as 200 here
     * so Zend Framework does not interfere with the status code).
     */
    public function createAction(): void
    {
        $raw  = $this->getRequest()->getRawBody();
        $body = json_decode($raw ?: '{}', true) ?: [];

        $curl = curl_init(self::API_BASE . 'api/v2/audio/linein');
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => 'POST',
            CURLOPT_POSTFIELDS     => json_encode($body),
            CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
        ]);
        $resp   = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        $this->getResponse()->setHttpResponseCode($status === 201 ? 200 : $status);
        $this->_helper->json(json_decode($resp ?: '{}', true));
    }

    /**
     * POST /linein/update/<id> — partially update an existing line-in source.
     *
     * ``id`` is the domain UUID (linein_id), passed as a route parameter.
     */
    public function updateAction(): void
    {
        $lineinId = $this->getRequest()->getParam('id', '');
        $raw      = $this->getRequest()->getRawBody();
        $body     = json_decode($raw ?: '{}', true) ?: [];

        $curl = curl_init(self::API_BASE . 'api/v2/audio/linein/' . urlencode($lineinId));
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => 'PATCH',
            CURLOPT_POSTFIELDS     => json_encode($body),
            CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
        ]);
        $resp   = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        $this->getResponse()->setHttpResponseCode($status);
        $this->_helper->json(json_decode($resp ?: '{}', true));
    }

    /**
     * POST /linein/delete/<id> — delete a line-in source.
     */
    public function deleteAction(): void
    {
        $lineinId = $this->getRequest()->getParam('id', '');

        $curl = curl_init(self::API_BASE . 'api/v2/audio/linein/' . urlencode($lineinId));
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => 'DELETE',
        ]);
        curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        // 204 → return empty success envelope
        if ($status === 204) {
            $this->_helper->json(['success' => true]);
        } else {
            $this->getResponse()->setHttpResponseCode($status);
            $this->_helper->json(['success' => false]);
        }
    }

    // -------------------------------------------------------------------------
    // RASTATIME 2026-05-12 — Library actions (Phase A.2)
    //
    // These mirror WebstreamController::newAction / editAction / saveAction
    // so the Media-Library can offer Line-In as a fifth item type
    // (Tracks, Playlists, Smart Blocks, Webstreams, Line-Ins).
    //
    // Persistence still goes through the Django REST API at
    // /api/v2/audio/linein — these PHP actions render the edit dialog
    // and translate the JS Library's POST shape to the API shape.
    // -------------------------------------------------------------------------

    /**
     * GET /linein/new — render the "new line-in" edit dialog.
     *
     * Does NOT persist anything; just hands the library JS an empty
     * Application_Model_Linein wrapped in the same html-render envelope
     * that WebstreamController::newAction uses.
     */
    public function newAction(): void
    {
        // Clear any open playlist session (CC-4196 pattern from Webstream).
        Application_Model_Library::changePlaylist(null, null);

        $this->view->obj    = new Application_Model_Linein();
        $this->view->action = 'new';
        $this->view->html   = $this->view->render('linein/linein.phtml');
    }

    /**
     * GET /linein/edit?id=<linein_uuid> — render the edit dialog for
     * an existing line-in.  ``id`` is the domain UUID (linein_id).
     */
    public function editAction(): void
    {
        $idParam = $this->getRequest()->getParam('id', '');
        if ($idParam === '') {
            throw new Exception("Missing parameter 'id'");
        }

        // The Library data-table feeds us the DB integer PK
        // (``rastatime_linein.id`` from the SQL UNION), but the
        // Django REST API uses the domain UUID (``linein_id``).
        // Resolve int → UUID here via direct SQL; the alternative
        // (re-shaping the Library UNION to surface the UUID) would
        // ripple into Drag-into-Show's cc_schedule.linein_id FK,
        // which is integer-typed.
        if (ctype_digit((string) $idParam)) {
            $row = Application_Common_Database::prepareAndExecute(
                'SELECT linein_id FROM rastatime_linein WHERE id = :id',
                [':id' => (int) $idParam],
                Application_Common_Database::SINGLE
            );
            $lineinId = $row ? (string) $row['linein_id'] : '';
        } else {
            // Already a UUID — used by direct deep-link URLs and tests.
            $lineinId = (string) $idParam;
        }

        if ($lineinId === '') {
            $this->view->html = "<div class='errors'>"
                . _('Line-In not found.') . '</div>';
            $this->view->action = 'edit';
            return;
        }

        // Fetch the current state from the Django API.
        $curl = curl_init(self::API_BASE . 'api/v2/audio/linein/' . urlencode($lineinId));
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
        $body   = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        if ($status !== 200 || !is_string($body)) {
            $this->view->html = "<div class='errors'>"
                . _('Line-In not found.') . '</div>';
            $this->view->action = 'edit';
            return;
        }

        $data = json_decode($body, true) ?: [];
        if (empty($data) || !isset($data['id'])) {
            $this->view->html = "<div class='errors'>"
                . _('Line-In not found.') . '</div>';
            $this->view->action = 'edit';
            return;
        }

        Application_Model_Library::changePlaylist($lineinId, 'linein');

        $this->view->obj    = new Application_Model_Linein($data);
        $this->view->id     = $lineinId;
        $this->view->type   = 'linein';
        $this->view->action = 'edit';
        $this->view->html   = $this->view->render('linein/linein.phtml');
    }

    /**
     * POST /linein/save — persist the edit dialog's form.
     *
     * Routes to POST (create) or PATCH (update) on the Django API
     * depending on whether an ``id`` is present.  Returns a small JSON
     * envelope the library JS uses to update its row count and select
     * the newly created item.
     */
    public function saveAction(): void
    {
        $request = $this->getRequest();
        $id      = trim($request->getParam('id', ''));
        $name    = trim($request->getParam('name', ''));
        $desc    = trim($request->getParam('description', ''));
        $dev     = trim($request->getParam('device_id', ''));
        $devName = trim($request->getParam('device_name', ''));
        $lenStr  = trim($request->getParam('length', '00:30:00'));
        // RASTATIME 2026-09-17 (consolidation) - channels come from the
        // dialog now: comma-separated 0-based ints ("0,1"); anything
        // malformed falls back to stereo 1/2.  No enabled field - the
        // operator dropped the toggle (an existing line-in may always
        // be used); creates pin enabled=true, updates leave it alone.
        $chanStr = trim($request->getParam('channels', ''));
        // RASTATIME 2026-10-02 - static input gain (dB), clamped like the
        // webstream one (WebstreamController::saveAction); empty or
        // non-numeric -> 0 = unchanged.
        $rawGain = trim((string) $request->getParam('input_gain_db', ''));
        $gainDb  = is_numeric($rawGain) ? max(-20.0, min(20.0, (float) $rawGain)) : 0.0;
        $mapping = [0, 1];
        if ($chanStr !== '' && preg_match('/^\d+(,\d+)*$/', $chanStr)) {
            $mapping = array_map('intval', explode(',', $chanStr));
        }

        // Parse HH:MM:SS into seconds.  Empty / malformed → null
        // (= "use default at consumption time").
        $lenSec = self::_parseHmsToSeconds($lenStr);

        // Build the Django payload.  ``channel_mapping`` and the
        // ``enabled`` / ``priority`` advanced fields are left at the
        // existing values on PATCH; on POST we default them.
        //
        // RASTATIME 2026-05-14 — ``device_name`` is the OS-friendly
        // label of the picked device at save time.  Persisted so the
        // playout's resolver can fall back to name-match if the
        // ``device_id`` (USB endpoint GUID) no longer resolves after
        // a reboot.  Older clients that don't send it pass "" which
        // makes the fallback a no-op (preflight behaves as before).
        $payload = [
            'name'            => $name,
            'device_id'       => $dev,
            'device_name'     => $devName,
            'description'     => $desc,
            'length_seconds'  => $lenSec,
            'channel_mapping' => $mapping,
            'input_gain_db'   => $gainDb,
        ];

        if ($id === '') {
            // CREATE
            $payload['enabled']         = true;
            $payload['priority']        = 0;
            $method = 'POST';
            $url    = self::API_BASE . 'api/v2/audio/linein';
        } else {
            // UPDATE
            $method = 'PATCH';
            $url    = self::API_BASE . 'api/v2/audio/linein/' . urlencode($id);
        }

        $curl = curl_init($url);
        curl_setopt_array($curl, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST  => $method,
            CURLOPT_POSTFIELDS     => json_encode($payload),
            CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
        ]);
        $body   = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        $data = json_decode($body ?: '{}', true) ?: [];

        if ($status >= 400) {
            $this->view->statusMessage = "<div class='errors'>"
                . htmlspecialchars($data['error'] ?? _('Invalid form values.'))
                . '</div>';
            $this->view->lineinId = '';
            return;
        }

        Application_Model_Library::changePlaylist($data['id'] ?? '', 'linein');

        $this->view->statusMessage = "<div class='success'>"
            . _('Line-In saved.') . '</div>';
        $this->view->lineinId = $data['id'] ?? '';
        // Mirror Webstream's response shape so the library JS treats
        // this the same way.
        $this->view->length = $lenStr;
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------

    /**
     * Parse ``HH:MM:SS`` or ``MM:SS`` into total seconds.
     * Returns ``null`` if the input is empty or unparseable so the
     * caller (and ultimately the Django field) can fall back to the
     * default 30-minute length.
     */
    private static function _parseHmsToSeconds(string $s): ?int
    {
        if ($s === '') {
            return null;
        }
        $parts = explode(':', $s);
        if (count($parts) === 3) {
            [$h, $m, $sec] = $parts;
        } elseif (count($parts) === 2) {
            $h = '0';
            [$m, $sec] = $parts;
        } else {
            return null;
        }
        if (!ctype_digit($h) || !ctype_digit($m) || !ctype_digit($sec)) {
            return null;
        }
        return ((int) $h) * 3600 + ((int) $m) * 60 + ((int) $sec);
    }
}
