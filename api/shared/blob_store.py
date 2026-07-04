from datetime import datetime, timedelta, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas

from shared.config import Settings
from shared.models import build_input_blob_path, sanitize_filename


class BlobStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        if settings.storage_connection_string:
            self._service_client = BlobServiceClient.from_connection_string(settings.storage_connection_string)
        else:
            self._service_client = BlobServiceClient(account_url=settings.storage_account_url, credential=DefaultAzureCredential())

    def upload_input_blob(
        self,
        *,
        project_name: str,
        dataset_id: str,
        run_id: str,
        filename: str,
        body: bytes,
        content_type: str,
    ) -> tuple[str, str]:
        cleaned_filename = sanitize_filename(filename)
        blob_path = build_input_blob_path(project_name, dataset_id, run_id, cleaned_filename)
        blob_client = self._service_client.get_blob_client(container=self._settings.raw_input_container, blob=blob_path)
        blob_client.upload_blob(
            body,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
        return self._settings.raw_input_container, blob_path

    def generate_download_url(self, *, blob_container: str, blob_path: str) -> tuple[str, str]:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=self._settings.sas_expiry_minutes)
        blob_client = self._service_client.get_blob_client(container=blob_container, blob=blob_path)
        user_delegation_key = self._service_client.get_user_delegation_key(
            key_start_time=datetime.now(timezone.utc),
            key_expiry_time=expiry,
        )
        sas_token = generate_blob_sas(
            account_name=self._settings.storage_account_name,
            container_name=blob_container,
            blob_name=blob_path,
            user_delegation_key=user_delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        return f'{blob_client.url}?{sas_token}', expiry.isoformat().replace('+00:00', 'Z')