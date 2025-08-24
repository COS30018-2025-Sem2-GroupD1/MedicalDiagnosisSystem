# Save final post-process to Google Drive
import os
import json
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("drive-saver")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    logger.addHandler(handler)


class DriveSaver:
    """Google Drive uploader with flexible mimetype and default folder id."""

    def __init__(self, default_folder_id: Optional[str] = None):
        self.service = None
        self.folder_id = default_folder_id or "1JvW7its63E58fLxurH8ZdhxzdpcMrMbt"
        self._initialize_service()

    def _initialize_service(self):
        try:
            creds_env = os.getenv("GDRIVE_CREDENTIALS_JSON")
            if not creds_env:
                raise RuntimeError("GDRIVE_CREDENTIALS_JSON not set")
            creds_dict = json.loads(creds_env)
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
            )
            self.service = build("drive", "v3", credentials=creds)
            logger.info("✅ Google Drive service initialized")
        except Exception as e:
            logger.error(f"❌ Drive initialization failed: {e}")
            self.service = None

    def upload_file_to_drive(self, file_path: str, folder_id: Optional[str] = None, mimetype: Optional[str] = None) -> bool:
        if not self.service:
            logger.error("❌ Drive service not initialized")
            return False
        try:
            target_folder = folder_id or self.folder_id
            name = os.path.basename(file_path)
            media = MediaFileUpload(file_path, mimetype=mimetype or "application/octet-stream")
            metadata = {"name": name, "parents": [target_folder]}
            self.service.files().create(body=metadata, media_body=media, fields="id").execute()
            logger.info(f"✅ Uploaded '{name}' to Drive (folder: {target_folder})")
            return True
        except Exception as e:
            logger.error(f"❌ Drive upload failed: {e}")
            return False

    def is_service_available(self) -> bool:
        return self.service is not None

    def set_folder_id(self, folder_id: str):
        self.folder_id = folder_id
        logger.info(f"📁 Default folder ID updated: {folder_id}")
