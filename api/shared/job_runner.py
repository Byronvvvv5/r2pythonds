from typing import Any

import requests
from azure.identity import DefaultAzureCredential

from shared.config import Settings


class ContainerAppsJobRunner:
    api_version = '2024-03-01'

    def __init__(self, settings: Settings):
        self._settings = settings
        self._credential = DefaultAzureCredential()

    def trigger_run(self, *, run_document: dict[str, Any], input_prefix: str) -> dict[str, Any]:
        token = self._credential.get_token('https://management.azure.com/.default').token
        url = (
            f'https://management.azure.com/subscriptions/{self._settings.azure_subscription_id}'
            f'/resourceGroups/{self._settings.azure_resource_group}'
            f'/providers/Microsoft.App/jobs/{self._settings.container_job_name}/start'
            f'?api-version={self.api_version}'
        )

        payload: dict[str, Any] = {}
        if self._settings.container_job_image:
            payload = {
                'containers': [
                    {
                        'name': self._settings.container_job_container_name,
                        'image': self._settings.container_job_image,
                        'env': [
                            {'name': 'RUN_ID', 'value': run_document['runId']},
                            {'name': 'PROJECT_NAME', 'value': run_document['projectName']},
                            {'name': 'DATASET_ID', 'value': run_document['datasetId']},
                            {'name': 'INPUT_PREFIX', 'value': input_prefix},
                        ],
                        'resources': {
                            'cpu': self._settings.container_job_cpu,
                            'memory': self._settings.container_job_memory,
                        },
                    }
                ]
            }

        response = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=30,
        )
        response.raise_for_status()

        if response.text:
            return response.json()

        return {
            'statusCode': response.status_code,
            'location': response.headers.get('Location'),
        }