"""
RASTATIME 2026-09-16 - backup endpoints (Settings -> Backup, stage 1).

    GET  /api/v2/storage/backup           folder setting, health, backup
                                           list, job status
    POST /api/v2/storage/backup/validate  {"path": ...} -> ok / errors
    POST /api/v2/storage/backup/folder    {"path": ...} -> save the setting
    POST /api/v2/storage/backup/run       -> 202 + job status
    GET  /api/v2/storage/backup/download?name=rastatime-backup-....zip

All of them use the API's default permission (API key or logged-in user);
the Backup page reaches them through PHP actions behind the operator
login and a CSRF token.  Restores stay CLI/offline (BACKUP.md section 7).
"""
from __future__ import annotations

import os

from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import backup as storage_backup


def _payload() -> dict:
    folder = storage_backup.get_backup_folder()
    data = {
        "folder": folder,
        "configured": bool(folder),
        "folder_ok": bool(folder) and os.path.isdir(folder),
        "backups": storage_backup.list_backups(folder),
        "job": storage_backup.JOB.status(),
    }
    return data


class BackupStatusView(APIView):
    def get(self, request):
        return Response(_payload())


class BackupValidateView(APIView):
    def post(self, request):
        path = str((request.data or {}).get("path", ""))
        return Response(storage_backup.validate_folder(path))


class BackupFolderView(APIView):
    def post(self, request):
        path = str((request.data or {}).get("path", ""))
        check = storage_backup.validate_folder(path)
        if not check["ok"]:
            return Response({"errors": check["errors"]}, status=status.HTTP_400_BAD_REQUEST)
        storage_backup.set_backup_folder(check["target"])
        return Response(_payload())


class BackupRunView(APIView):
    def post(self, request):
        try:
            job = storage_backup.JOB.start()
        except storage_backup.BackupInProgress:
            return Response(
                {"errors": ["A backup is already running."], "job": storage_backup.JOB.status()},
                status=status.HTTP_409_CONFLICT,
            )
        except storage_backup.InvalidFolder as exc:
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:                  # pg_dump missing
            return Response({"errors": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"job": job}, status=status.HTTP_202_ACCEPTED)


class BackupDownloadView(APIView):
    def get(self, request):
        name = str(request.query_params.get("name", ""))
        path = storage_backup.backup_file_path(name)
        if not path:
            return Response({"errors": ["No such backup."]}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            open(path, "rb"),  # noqa: SIM115
            content_type="application/zip",
            as_attachment=True,
            filename=name,
        )
