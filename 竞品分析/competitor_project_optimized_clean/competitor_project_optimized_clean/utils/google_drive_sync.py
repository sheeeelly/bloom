from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DOCS_SCOPE = "https://www.googleapis.com/auth/documents"


def _load_credentials(credentials_json: str, scopes: list[str]):
    try:
        from oauth2client.service_account import ServiceAccountCredentials
    except Exception as exc:
        raise RuntimeError("缺少 oauth2client，无法认证 Google 服务账号。") from exc

    if os.path.exists(credentials_json):
        return ServiceAccountCredentials.from_json_keyfile_name(credentials_json, scopes)

    try:
        creds_dict = json.loads(credentials_json)
    except json.JSONDecodeError as exc:
        raise FileNotFoundError("Google credentials 既不是文件路径，也不是 JSON 字符串。") from exc
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)


def _build_service(name: str, version: str, credentials_json: str, scopes: list[str]):
    try:
        from googleapiclient.discovery import build
    except Exception as exc:
        raise RuntimeError("缺少 google-api-python-client，无法调用 Google Drive/Docs API。") from exc

    creds = _load_credentials(credentials_json, scopes)
    return build(name, version, credentials=creds, cache_discovery=False)


class GoogleDrivePublisher:
    def __init__(self, credentials_json: str, parent_folder_id: str = "") -> None:
        self.credentials_json = credentials_json
        self.parent_folder_id = parent_folder_id
        self.drive = _build_service("drive", "v3", credentials_json, [DRIVE_SCOPE, DOCS_SCOPE])
        self.docs = _build_service("docs", "v1", credentials_json, [DRIVE_SCOPE, DOCS_SCOPE])

    def ensure_folder(self, name: str, parent_folder_id: str | None = None) -> dict[str, str]:
        parent = parent_folder_id if parent_folder_id is not None else self.parent_folder_id
        query_parts = [
            "mimeType='application/vnd.google-apps.folder'",
            f"name='{name.replace(chr(39), chr(92) + chr(39))}'",
            "trashed=false",
        ]
        if parent:
            query_parts.append(f"'{parent}' in parents")
        response = self.drive.files().list(
            q=" and ".join(query_parts),
            fields="files(id,name,webViewLink)",
            pageSize=1,
        ).execute()
        files = response.get("files", [])
        if files:
            file = files[0]
            return {"id": file["id"], "name": file["name"], "url": file.get("webViewLink", "")}

        metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent:
            metadata["parents"] = [parent]
        folder = self.drive.files().create(
            body=metadata,
            fields="id,name,webViewLink",
        ).execute()
        return {"id": folder["id"], "name": folder["name"], "url": folder.get("webViewLink", "")}

    def upload_file(self, path: Path, folder_id: str, name: str | None = None, mime_type: str | None = None) -> dict[str, str]:
        try:
            from googleapiclient.http import MediaFileUpload
        except Exception as exc:
            raise RuntimeError("缺少 google-api-python-client，无法上传文件。") from exc

        metadata = {"name": name or path.name, "parents": [folder_id]}
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
        file = self.drive.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
        ).execute()
        return {"id": file["id"], "name": file["name"], "url": file.get("webViewLink", "")}

    def create_doc_from_markdown(self, title: str, markdown_path: Path, folder_id: str) -> dict[str, str]:
        document = self.docs.documents().create(body={"title": title}).execute()
        document_id = document["documentId"]
        text = markdown_path.read_text(encoding="utf-8")
        self.docs.documents().batchUpdate(
            documentId=document_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": text,
                        }
                    }
                ]
            },
        ).execute()

        self.drive.files().update(
            fileId=document_id,
            addParents=folder_id,
            fields="id,name,webViewLink",
        ).execute()
        file = self.drive.files().get(fileId=document_id, fields="id,name,webViewLink").execute()
        return {"id": file["id"], "name": file["name"], "url": file.get("webViewLink", "")}
