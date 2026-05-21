<?php

/**
 * Application_Model_Linein — thin PHP wrapper around a single line-in row.
 *
 * Mirrors the role of :class:`Application_Model_Webstream` for the new
 * Media-Library Line-In feature (Phase A, RASTATIME 2026-05-12).
 *
 * Unlike Webstream — which is backed by a Propel-generated CcWebstream
 * Active Record — line-ins live in the Django-managed
 * ``rastatime_linein`` table.  This wrapper therefore takes a plain
 * associative array (typically the JSON body returned by
 * ``GET /api/v2/audio/linein[/<linein_id>]``) and exposes the small
 * set of getters that the linein.phtml view template needs.
 *
 * Why no Propel mapping
 * ---------------------
 * Adding rastatime_linein to schema.xml would mean teaching Propel
 * about a non-cc_* table on a non-Propel migration cadence.  Net cost
 * exceeds benefit — all line-in persistence happens through the
 * Django REST API already, and the PHP side only needs read/format
 * access for the edit dialog.
 */
class Application_Model_Linein
{
    /** @var array Linein record as returned by the Django API. */
    private $data;

    /**
     * Default Library duration if the operator hasn't set one.
     * Matches the Webstream Library default of 30 minutes.
     */
    private const DEFAULT_LENGTH_SECONDS = 1800;

    /**
     * @param array $data  Decoded JSON dict from the Django Line-In API.
     *                     Required keys (when editing): id, name, device_id.
     *                     Optional keys: description, length_seconds,
     *                     channel_mapping, enabled, priority.
     *                     Pass an empty array for a "new" stub.
     */
    public function __construct(array $data = [])
    {
        $this->data = array_merge([
            'id'              => '',
            'name'            => _('Untitled Line-In'),
            'description'     => '',
            'device_id'       => '',
            'length_seconds'  => null,
            'enabled'         => true,
            'priority'        => 0,
            'channel_mapping' => [0, 1],
        ], $data);
    }

    /** Domain UUID (empty string for an unsaved stub). */
    public function getId(): string
    {
        return (string) $this->data['id'];
    }

    public function getName(): string
    {
        return (string) $this->data['name'];
    }

    public function getDescription(): string
    {
        return (string) ($this->data['description'] ?? '');
    }

    /** Stable audio-endpoint ID currently selected for this line-in. */
    public function getDeviceId(): string
    {
        return (string) ($this->data['device_id'] ?? '');
    }

    /**
     * Default Library duration formatted as ``HH:MM:SS`` for the form
     * input (matches Webstream's ``$obj->getDefaultLength()``).
     */
    public function getDefaultLength(): string
    {
        $sec = $this->data['length_seconds'];
        if (!is_int($sec) || $sec < 0) {
            $sec = self::DEFAULT_LENGTH_SECONDS;
        }
        return gmdate('H:i:s', $sec);
    }

    /** Raw seconds value (or ``null`` for "use default at consumption"). */
    public function getLengthSeconds(): ?int
    {
        $sec = $this->data['length_seconds'] ?? null;
        return is_int($sec) ? $sec : null;
    }

    public function getChannelMapping(): array
    {
        $m = $this->data['channel_mapping'] ?? [0, 1];
        return is_array($m) ? $m : [0, 1];
    }
}
