import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..download import download_episode
from ..models import ImportedPodcast, Podcast, PodcastEpisode, StationPodcast
from ..serializers import (
    ImportedPodcastSerializer,
    PodcastEpisodeSerializer,
    PodcastSerializer,
    StationPodcastSerializer,
)

logger = logging.getLogger(__name__)


class PodcastViewSet(viewsets.ModelViewSet):
    queryset = Podcast.objects.all()
    serializer_class = PodcastSerializer
    model_permission_name = "podcast"


class PodcastEpisodeViewSet(viewsets.ModelViewSet):
    queryset = PodcastEpisode.objects.all()
    serializer_class = PodcastEpisodeSerializer
    model_permission_name = "podcastepisode"

    @action(detail=True, methods=["post"])
    def download(self, request, pk=None):
        """
        Synchronously download a podcast episode and import it into the
        media library.

        T-PODCAST-1: Replaces the defunct Celery/RabbitMQ dispatch chain.
        Fetches the audio file, tags it, writes it directly to the media
        store, and creates the cc_files record via Django ORM.

        Returns HTTP 200 with result JSON on success,
                HTTP 500 with error JSON on failure.
        """
        episode = self.get_object()
        podcast = episode.podcast

        # Determine album-override + auto-expiry + default-track-type
        # from the ImportedPodcast record
        override_album = False
        auto_expiry_enabled = False
        auto_expiry_days = None
        default_track_type_id = None
        try:
            imported = ImportedPodcast.objects.get(podcast=podcast)
            override_album = bool(imported.override_album)
            # RASTATIME 2026-05-16 - Podcast Auto-Expiry pickup.
            auto_expiry_enabled = bool(imported.auto_expiry_enabled)
            auto_expiry_days = imported.auto_expiry_days
            # RASTATIME 2026-05-17 - Per-podcast default Track-Type pickup.
            # Read the FK column directly (avoids a SELECT on cc_track_types).
            default_track_type_id = imported.default_track_type_id
        except ImportedPodcast.DoesNotExist:
            pass

        # RASTATIME 2026-09-16 - the root is a setting; downloads pause
        # while the library is being moved.
        from ...storage import move as storage_move  # noqa: PLC0415
        from ...storage.root import get_storage_root  # noqa: PLC0415
        if storage_move.JOB.is_locked():
            return Response(
                {"error": "The media library is being moved - podcast downloads are paused."},
                status=status.HTTP_409_CONFLICT,
            )
        storage_path = get_storage_root()
        owner_id = podcast.owner_id  # cc_subjs.id — may be None

        result = download_episode(
            episode_id=episode.id,
            episode_url=episode.download_url,
            episode_title=episode.episode_title or None,
            podcast_name=podcast.title,
            override_album=override_album,
            storage_path=storage_path,
            owner_id=owner_id,
            auto_expiry_enabled=auto_expiry_enabled,
            auto_expiry_days=auto_expiry_days,
            default_track_type_id=default_track_type_id,
        )

        if result.get("status") == 1:
            episode.file_id = result["fileid"]
            episode.save(update_fields=["file_id"])
            logger.info(
                "podcast episode %d downloaded successfully, file_id=%d",
                episode.id,
                result["fileid"],
            )
            return Response(result)

        logger.error(
            "podcast episode %d download failed: %s",
            episode.id,
            result.get("error", "unknown"),
        )
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StationPodcastViewSet(viewsets.ModelViewSet):
    queryset = StationPodcast.objects.all()
    serializer_class = StationPodcastSerializer
    model_permission_name = "station"


class ImportedPodcastViewSet(viewsets.ModelViewSet):
    queryset = ImportedPodcast.objects.all()
    serializer_class = ImportedPodcastSerializer
    model_permission_name = "importedpodcast"
