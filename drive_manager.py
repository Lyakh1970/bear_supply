from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from google_auth import load_credentials

def upload_to_drive(
    service_account_file: str,
    local_path: str,
    filename: str,
    folder_id: str | None = None
) -> str:
    creds = load_credentials(service_account_file)
    service = build("drive", "v3", credentials=creds)

    metadata: dict = {"name": filename}
    # IMPORTANT: folder_id optional. If empty -> upload to Drive root (no parents) => no 404.
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(local_path, resumable=True)

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