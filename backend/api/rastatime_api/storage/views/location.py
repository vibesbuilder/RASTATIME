"""
RASTATIME 2026-09-16 - storage location endpoints (Media Library Location).

    GET  /api/v2/storage/location       effective root, source, health,
                                         library size, move status
    POST /api/v2/storage/move/validate  {"path": ...} -> ok / errors / space
    POST /api/v2/storage/move/start     {"path": ...} -> 202 + status
    POST /api/v2/storage/move/cancel    -> status
    GET  /api/v2/storage/move/status    -> status

All of them use the API's default permission (API key or logged-in user);
the Local Machine page reaches them through PHP actions behind the
operator login and a CSRF token.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import move as storage_move
from .. import root as storage_root


def _location_payload() -> dict:
    info = storage_root.root_info()
    files, size = storage_root.library_size(info["root"]) if info["exists"] else (0, 0)
    age = storage_root.library_size_age(info["root"]) if info["exists"] else None
    info.update(
        library_files=files,
        library_bytes=size,
        library_size_age_seconds=None if age is None else int(age),
        move=storage_move.JOB.status(),
    )
    return info


class StorageLocationView(APIView):
    def get(self, request):
        return Response(_location_payload())


class StorageMoveValidateView(APIView):
    def post(self, request):
        path = str((request.data or {}).get("path", ""))
        source = storage_root.get_storage_root(refresh=True)
        _files, size = storage_root.library_size(source, refresh=True)  # exact for the move check
        return Response(storage_move.validate_target(path, source, size))


class StorageMoveStartView(APIView):
    def post(self, request):
        path = str((request.data or {}).get("path", ""))
        try:
            state = storage_move.JOB.start(path)
        except storage_move.MoveInProgress:
            return Response(
                {"errors": ["A move is already running."], "move": storage_move.JOB.status()},
                status=status.HTTP_409_CONFLICT,
            )
        except storage_move.InvalidTarget as exc:
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"move": state}, status=status.HTTP_202_ACCEPTED)


class StorageMoveCancelView(APIView):
    def post(self, request):
        return Response({"move": storage_move.JOB.cancel()})


class StorageMoveStatusView(APIView):
    def get(self, request):
        return Response({"move": storage_move.JOB.status()})
