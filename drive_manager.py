import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from google_auth import load_credentials

logger = logging.getLogger(__name__)


def upload_to_drive(
    service_account_file: str,
    local_path: str,
    filename: str,
    folder_id: str | None = None
) -> str:
    logger.info(f"upload_to_drive: filename={filename}, folder_id={folder_id}")
    
    creds = load_credentials(service_account_file)
    service = build("drive", "v3", credentials=creds)

    metadata: dict = {"name": filename}
    # IMPORTANT: folder_id MUST be set for Service Account (no own storage quota)
    if folder_id:
        metadata["parents"] = [folder_id]
        logger.info(f"Will upload to folder: {folder_id}")
    else:
        logger.warning("No folder_id specified! Service Account has no storage quota.")

    media = MediaFileUpload(local_path, resumable=True)
    logger.info(f"Uploading file with metadata: {metadata}")

    try:
        created = service.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"Drive upload failed: {e}") from e

    # webViewLink бывает не всегда, тогда строим ручками
    file_id = created.get("id")
    link = created.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
    return link