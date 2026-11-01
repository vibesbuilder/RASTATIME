import logging
import mimetypes
import os
from os import remove
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse
from django.utils.encoding import filepath_to_uri
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException

from ...schedule.models import Schedule
from ..models import File
from ..root import get_storage_root
from ..serializers import FileSerializer

logger = logging.getLogger(__name__)

# RASTATIME: Detect whether we're behind Nginx (X-Accel-Redirect) or
# serving directly via Waitress on Windows.
_USE_NGINX_REDIRECT = os.environ.get("RASTATIME_USE_NGINX", "").lower() in (
    "1",
    "true",
    "yes",
)


class FileInUse(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The file is currently used"
    default_code = "file_in_use"


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    model_permission_name = "file"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ("md5", "genre")

    # pylint: disable=invalid-name,unused-argument
    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):
        instance: File = self.get_object()

        if _USE_NGINX_REDIRECT:
            # Nginx serves the file via X-Accel-Redirect (Linux production).
            response = HttpResponse()
            redirect_uri = filepath_to_uri(os.path.join("/api/_media", instance.filepath))
            response["X-Accel-Redirect"] = redirect_uri
            return response

        # RASTATIME: Serve file directly (Waitress / Windows).
        # Strip leading "/" from filepath — on Windows, Path() / "/foo"
        # treats the right side as absolute and discards the base.
        # RASTATIME 2026-09-16 - the root is a setting (Local Machine)
        storage_root = get_storage_root()
        raw_filepath = instance.filepath or ""
        rel_path = raw_filepath.lstrip("/")
        file_path = Path(storage_root) / rel_path
        if not file_path.is_file():
            logger.error(
                "File not found — storage_root=%r, raw=%r, rel=%r, resolved=%s",
                storage_root,
                raw_filepath,
                rel_path,
                file_path,
            )
            raise Http404(
                f"File not found: resolved={file_path}, storage={storage_root}, raw={raw_filepath}"
            )

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return FileResponse(
            open(file_path, "rb"),  # noqa: SIM115
            content_type=content_type,
            as_attachment=True,
            filename=file_path.name,
        )

    def perform_destroy(self, instance: File):
        if Schedule.is_file_scheduled_in_the_future(file_id=instance.id):
            raise FileInUse("file is scheduled in the future")

        try:
            if instance.filepath is None:
                logger.warning("file does not have a filepath: %d", instance.id)
                return

            rel = instance.filepath.lstrip("/") if instance.filepath else ""
            path = os.path.join(get_storage_root(), rel)

            if not os.path.isfile(path):
                logger.warning("file does not exist in storage: %d", instance.id)
                return

            remove(path)
        except OSError as exception:
            raise APIException("could not delete file from storage") from exception
