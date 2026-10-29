from django.db import models


class File(models.Model):
    library = models.ForeignKey(
        "storage.Library",
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_column="track_type_id",
    )

    owner = models.ForeignKey(
        "core.User",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    class ImportStatus(models.IntegerChoices):
        SUCCESS = 0, "Success"
        PENDING = 1, "Pending"
        FAILED = 2, "Failed"

    import_status = models.IntegerField(
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING,
    )

    filepath = models.TextField(blank=True, null=True)
    size = models.IntegerField(db_column="filesize")
    exists = models.BooleanField(blank=True, null=True, db_column="file_exists")
    mime = models.CharField(max_length=255)
    md5 = models.CharField(max_length=32, blank=True, null=True)
    # RASTATIME 2026-10-14 - md5 of the original a lossless file was
    # converted from (legacy migration 0066); NULL = the stored file is
    # the original.  The duplicate check matches md5 OR source_md5.
    source_md5 = models.CharField(max_length=32, blank=True, null=True)

    hidden = models.BooleanField(blank=True, null=True)
    # RASTATIME 2026-05-16 - Track Expiry feature.
    expires_at = models.DateTimeField(blank=True, null=True)
    disabled = models.BooleanField(default=False)
    # RASTATIME 2026-09-27 - "No Fade during Crossover" (legacy migrations 0059 + 0060)
    no_fade_crossfade = models.BooleanField(default=False)
    # RASTATIME 2026-09-29 - "Exclude from Crossover" (legacy migration 0062):
    # the track never overlaps a neighbour, whatever its type says
    exclude_crossfade = models.BooleanField(default=False)
    # RASTATIME 2026-10-14 - stream metadata (legacy migration 0068):
    # NULL = as the track type, 1 = forward artist / title, 0 = do not
    icy_forward = models.SmallIntegerField(blank=True, null=True)
    # RASTATIME 2026-10-16 - teaser automation (legacy migrations 0069/0070):
    # how this jingle announces its shows ('show' any day, 'today',
    # 'tomorrow'); the shows themselves are rows of cc_file_teaser.  NULL =
    # not a teaser.
    teaser_type = models.CharField(max_length=16, blank=True, null=True)
    accessed = models.IntegerField(db_column="currentlyaccessing")
    scheduled = models.BooleanField(blank=True, null=True, db_column="is_scheduled")
    part_of_list = models.BooleanField(blank=True, null=True, db_column="is_playlist")

    created_at = models.DateTimeField(blank=True, null=True, db_column="utime")
    updated_at = models.DateTimeField(blank=True, null=True, db_column="mtime")
    last_played_at = models.DateTimeField(blank=True, null=True, db_column="lptime")

    edited_by = models.ForeignKey(
        "core.User",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="edited_files",
        db_column="editedby",
    )

    # Audio
    bit_rate = models.IntegerField(blank=True, null=True)
    sample_rate = models.IntegerField(blank=True, null=True)
    format = models.CharField(max_length=128, blank=True, null=True)  # ?
    channels = models.IntegerField(blank=True, null=True)
    length = models.DurationField(blank=True, null=True)

    bpm = models.IntegerField(blank=True, null=True)  # ?
    replay_gain = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
    )
    cue_in = models.DurationField(blank=True, null=True, db_column="cuein")
    cue_out = models.DurationField(blank=True, null=True, db_column="cueout")
    # RASTATIME 2026-09-28 - EBU R128 measurement (legacy migration 0061);
    # NULL = not measured yet.  The playout derives the per-track gain
    # from these when Loudness Normalization is "EBU R128".
    loudness_lufs = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    true_peak_dbtp = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    loudness_range_lu = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    # Metadata
    name = models.CharField(max_length=255)  # ?
    description = models.CharField(max_length=512, blank=True, null=True)  # ?

    artwork = models.CharField(max_length=512, blank=True, null=True)

    artist_name = models.CharField(max_length=512, blank=True, null=True)
    artist_url = models.CharField(max_length=512, blank=True, null=True)  # ?
    original_artist = models.CharField(max_length=512, blank=True, null=True)  # ?
    album_title = models.CharField(max_length=512, blank=True, null=True)
    track_title = models.CharField(max_length=512, blank=True, null=True)
    genre = models.CharField(max_length=64, blank=True, null=True)
    mood = models.CharField(max_length=64, blank=True, null=True)
    date = models.CharField(max_length=16, blank=True, null=True, db_column="year")
    track_number = models.IntegerField(blank=True, null=True)
    disc_number = models.CharField(max_length=8, blank=True, null=True)  # ?
    comment = models.TextField(blank=True, null=True, db_column="comments")
    language = models.CharField(max_length=512, blank=True, null=True)
    label = models.CharField(max_length=512, blank=True, null=True)
    copyright = models.CharField(max_length=512, blank=True, null=True)
    composer = models.CharField(max_length=512, blank=True, null=True)
    conductor = models.CharField(max_length=512, blank=True, null=True)
    orchestra = models.CharField(max_length=512, blank=True, null=True)  # ?
    encoder = models.CharField(max_length=64, blank=True, null=True)
    encoded_by = models.CharField(max_length=255, blank=True, null=True)  # ?
    isrc = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        db_column="isrc_number",
    )

    lyrics = models.TextField(blank=True, null=True)  # ?
    lyricist = models.CharField(max_length=512, blank=True, null=True)  # ?
    original_lyricist = models.CharField(max_length=512, blank=True, null=True)  # ?

    subject = models.CharField(max_length=512, blank=True, null=True)  # ?
    contributor = models.CharField(max_length=512, blank=True, null=True)  # ?
    rating = models.CharField(max_length=8, blank=True, null=True)  # ?
    url = models.CharField(max_length=1024, blank=True, null=True)  # ?
    info_url = models.CharField(max_length=512, blank=True, null=True)  # ?
    audio_source_url = models.CharField(max_length=512, blank=True, null=True)  # ?
    buy_this_url = models.CharField(max_length=512, blank=True, null=True)  # ?
    catalog_number = models.CharField(max_length=512, blank=True, null=True)  # ?

    radio_station_name = models.CharField(max_length=512, blank=True, null=True)  # ?
    radio_station_url = models.CharField(max_length=512, blank=True, null=True)  # ?

    report_datetime = models.CharField(max_length=32, blank=True, null=True)  # ?
    report_location = models.CharField(max_length=512, blank=True, null=True)  # ?
    report_organization = models.CharField(max_length=512, blank=True, null=True)  # ?

    def get_owner(self):
        return self.owner

    class Meta:
        managed = False
        db_table = "cc_files"
        permissions = [
            ("change_own_file", "Change the files where they are the owner"),
            ("delete_own_file", "Delete the files where they are the owner"),
        ]
