import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    storage_account_name: str
    storage_account_url: str
    raw_input_container: str
    processed_output_container: str
    cosmos_endpoint: str
    cosmos_database_name: str
    cosmos_runs_container: str
    cosmos_artifacts_container: str
    azure_subscription_id: str
    azure_resource_group: str
    container_job_name: str
    container_job_container_name: str
    container_job_image: str
    container_job_cpu: float
    container_job_memory: str
    api_auth_level: str
    sas_expiry_minutes: int
    storage_connection_string: str | None = None
    cosmos_connection_string: str | None = None


def _required(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise ConfigError(f'Missing required environment variable: {name}')


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    storage_account_name = _required('DATA_STORAGE_ACCOUNT_NAME')
    storage_account_url = os.getenv('DATA_STORAGE_ACCOUNT_URL', f'https://{storage_account_name}.blob.core.windows.net')

    return Settings(
        storage_account_name=storage_account_name,
        storage_account_url=storage_account_url,
        raw_input_container=_required('RAW_INPUT_CONTAINER'),
        processed_output_container=_required('PROCESSED_OUTPUT_CONTAINER'),
        cosmos_endpoint=_required('COSMOS_DB_ENDPOINT'),
        cosmos_database_name=_required('COSMOS_DB_DATABASE_NAME'),
        cosmos_runs_container=os.getenv('COSMOS_RUNS_CONTAINER', 'runs'),
        cosmos_artifacts_container=os.getenv('COSMOS_ARTIFACTS_CONTAINER', 'artifacts'),
        azure_subscription_id=_required('AZURE_SUBSCRIPTION_ID'),
        azure_resource_group=_required('AZURE_RESOURCE_GROUP'),
        container_job_name=_required('CONTAINER_JOB_NAME'),
        container_job_container_name=os.getenv('CONTAINER_JOB_CONTAINER_NAME', 'pipeline-runner'),
        container_job_image=os.getenv('CONTAINER_JOB_IMAGE', ''),
        container_job_cpu=float(os.getenv('CONTAINER_JOB_CPU', '1')),
        container_job_memory=os.getenv('CONTAINER_JOB_MEMORY', '2Gi'),
        api_auth_level=os.getenv('API_AUTH_LEVEL', 'FUNCTION'),
        sas_expiry_minutes=int(os.getenv('SAS_EXPIRY_MINUTES', '15')),
        storage_connection_string=os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
        cosmos_connection_string=os.getenv('COSMOS_DB_CONNECTION_STRING'),
    )