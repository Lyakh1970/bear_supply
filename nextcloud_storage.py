"""
Nextcloud storage backend для загрузки документов.

Использует WebDAV API для загрузки файлов и OCS Share API для создания публичных ссылок.
Адаптировано для cloud.bearcloud.one с обязательным паролем для public links.
"""

import os
import posixpath
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
from xml.etree import ElementTree as ET

import requests

import config

logger = logging.getLogger(__name__)


class NextcloudError(Exception):
    """Ошибка при работе с Nextcloud."""
    pass


@dataclass
class UploadResult:
    """Результат загрузки файла в Nextcloud."""
    success: bool
    storage_backend: str = "nextcloud"
    storage_path: Optional[str] = None
    public_url: Optional[str] = None
    share_password: Optional[str] = None
    upload_status: str = "pending"
    error: Optional[str] = None


def _normalize_base_url(base_url: str) -> str:
    """Убрать trailing slash."""
    return base_url.rstrip("/")


def _normalize_remote_folder(folder: str) -> str:
    """Нормализовать путь к папке."""
    folder = folder.strip()
    if not folder:
        return ""
    if not folder.startswith("/"):
        folder = "/" + folder
    return folder.rstrip("/")


def _build_storage_path(base_folder: str, subfolder: Optional[str], filename: str) -> str:
    """Построить полный путь в storage."""
    parts = []

    if base_folder:
        parts.extend([p for p in base_folder.strip("/").split("/") if p])

    if subfolder:
        parts.extend([p for p in subfolder.strip("/").split("/") if p])

    parts.append(filename)
    return "/" + "/".join(parts)


def _webdav_url(base_url: str, username: str, storage_path: str) -> str:
    """Построить WebDAV URL для пути."""
    encoded_path = "/".join(quote(part) for part in storage_path.strip("/").split("/"))
    return f"{base_url}/remote.php/dav/files/{quote(username)}/{encoded_path}"


def _shares_api_url(base_url: str) -> str:
    """URL для OCS Share API."""
    return f"{base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"


def _get_auth() -> tuple[str, str]:
    """Получить credentials для авторизации."""
    username = config.NEXTCLOUD_USERNAME
    password = config.NEXTCLOUD_PASSWORD
    if not username or not password:
        raise NextcloudError("NEXTCLOUD_USERNAME or NEXTCLOUD_PASSWORD not configured")
    return username, password


def _get_base_config() -> tuple[str, str]:
    """Получить базовые настройки."""
    base_url = config.NEXTCLOUD_BASE_URL
    if not base_url:
        raise NextcloudError("NEXTCLOUD_BASE_URL not configured")
    base_url = _normalize_base_url(base_url)
    base_folder = _normalize_remote_folder(config.NEXTCLOUD_BASE_FOLDER or "Documents/BearBox Docs/Finance")
    return base_url, base_folder


def ensure_folder(storage_folder: str, timeout: int = 60) -> None:
    """
    Создать папки рекурсивно в Nextcloud через WebDAV MKCOL.
    Безопасно вызывать даже если папки уже существуют.
    """
    base_url, _ = _get_base_config()
    username, password = _get_auth()

    clean_folder = storage_folder.strip("/")
    if not clean_folder:
        return

    parts = clean_folder.split("/")
    current = ""

    for part in parts:
        current = posixpath.join(current, part)
        url = f"{base_url}/remote.php/dav/files/{quote(username)}/{'/'.join(quote(p) for p in current.split('/'))}"

        resp = requests.request(
            "MKCOL",
            url,
            auth=(username, password),
            timeout=timeout,
        )

        if resp.status_code in (201, 405):  # 201 = created, 405 = already exists
            continue

        raise NextcloudError(
            f"Failed to create folder '{current}' in Nextcloud: "
            f"HTTP {resp.status_code} - {resp.text}"
        )


def _extract_share_url(xml_text: str) -> str:
    """Извлечь URL из XML ответа OCS API."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise NextcloudError(f"Failed to parse Nextcloud share XML: {e}") from e

    statuscode = root.findtext("./meta/statuscode")
    message = root.findtext("./meta/message")
    url = root.findtext("./data/url")

    if statuscode != "200":
        raise NextcloudError(
            f"Nextcloud share API returned statuscode={statuscode}, message={message}"
        )

    if not url:
        raise NextcloudError("Nextcloud share created but URL not found in response")

    return url


def create_public_share(storage_path: str, timeout: int = 60) -> dict:
    """
    Создать public share с паролем в Nextcloud.
    
    Returns:
        {"public_url": "...", "share_password": "..."}
    """
    base_url, _ = _get_base_config()
    username, password = _get_auth()
    shares_url = _shares_api_url(base_url)

    share_password = config.NEXTCLOUD_SHARE_PASSWORD or "BearBox2026!"

    payload = {
        "path": storage_path,
        "shareType": "3",  # 3 = public link
        "password": share_password,
    }

    logger.info(f"Creating Nextcloud public share for: {storage_path}")

    resp = requests.post(
        shares_url,
        auth=(username, password),
        headers={"OCS-APIRequest": "true"},
        data=payload,
        timeout=timeout,
    )

    if resp.status_code != 200:
        raise NextcloudError(
            f"Nextcloud share creation failed: HTTP {resp.status_code} - {resp.text}"
        )

    public_url = _extract_share_url(resp.text)

    return {
        "public_url": public_url,
        "share_password": share_password,
    }


def upload_file_to_nextcloud(
    local_path: str,
    original_filename: Optional[str] = None,
    subfolder: Optional[str] = None,
    timeout: int = 120,
) -> UploadResult:
    """
    Загрузить файл в Nextcloud и создать public share.
    
    Args:
        local_path: Путь к локальному файлу
        original_filename: Имя файла (если None, берётся из local_path)
        subfolder: Подпапка (например "2026/03")
        
    Returns:
        UploadResult с storage_path, public_url, share_password или error
    """
    try:
        if not os.path.isfile(local_path):
            return UploadResult(
                success=False,
                upload_status="failed",
                error=f"Local file does not exist: {local_path}"
            )

        base_url, base_folder = _get_base_config()
        username, password = _get_auth()

        filename = original_filename or os.path.basename(local_path)
        storage_path = _build_storage_path(base_folder, subfolder, filename)

        # 1. Создаём папку если нужно
        folder_only = posixpath.dirname(storage_path)
        ensure_folder(folder_only, timeout=timeout)

        # 2. Загружаем файл
        upload_url = _webdav_url(base_url, username, storage_path)
        logger.info(f"Uploading file to Nextcloud: {local_path} -> {storage_path}")

        with open(local_path, "rb") as f:
            resp = requests.put(
                upload_url,
                data=f,
                auth=(username, password),
                timeout=timeout,
            )

        if resp.status_code not in (201, 204):
            return UploadResult(
                success=False,
                storage_backend="nextcloud",
                storage_path=storage_path,
                upload_status="failed",
                error=f"Nextcloud upload failed: HTTP {resp.status_code} - {resp.text[:200]}"
            )

        # 3. Создаём public share
        try:
            share_data = create_public_share(storage_path=storage_path, timeout=timeout)
        except NextcloudError as e:
            # Файл загружен, но share не создался
            logger.warning(f"File uploaded but share failed: {e}")
            return UploadResult(
                success=True,
                storage_backend="nextcloud",
                storage_path=storage_path,
                public_url=None,
                share_password=None,
                upload_status="uploaded",
                error=f"Share creation failed: {e}"
            )

        return UploadResult(
            success=True,
            storage_backend="nextcloud",
            storage_path=storage_path,
            public_url=share_data["public_url"],
            share_password=share_data["share_password"],
            upload_status="uploaded",
        )

    except NextcloudError as e:
        logger.error(f"Nextcloud error: {e}")
        return UploadResult(
            success=False,
            storage_backend="nextcloud",
            upload_status="failed",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading to Nextcloud: {e}")
        return UploadResult(
            success=False,
            storage_backend="nextcloud",
            upload_status="failed",
            error=str(e)
        )


def test_connection() -> bool:
    """Проверить подключение к Nextcloud."""
    try:
        base_url, _ = _get_base_config()
        username, password = _get_auth()
        
        url = f"{base_url}/remote.php/dav/files/{quote(username)}/"
        resp = requests.request("PROPFIND", url, auth=(username, password), timeout=10, headers={"Depth": "0"})
        
        if resp.status_code in (200, 207):
            logger.info("Nextcloud connection OK")
            return True
        
        logger.error(f"Nextcloud connection failed: HTTP {resp.status_code}")
        return False
    except NextcloudError as e:
        logger.warning(f"Nextcloud not configured: {e}")
        return False
    except Exception as e:
        logger.error(f"Nextcloud connection error: {e}")
        return False
