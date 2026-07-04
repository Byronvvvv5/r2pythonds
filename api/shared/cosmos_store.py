from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from shared.config import Settings


class CosmosStore:
    def __init__(self, settings: Settings):
        if settings.cosmos_connection_string:
            self._client = CosmosClient.from_connection_string(settings.cosmos_connection_string)
        else:
            self._client = CosmosClient(settings.cosmos_endpoint, credential=DefaultAzureCredential())

        database = self._client.get_database_client(settings.cosmos_database_name)
        self._runs = database.get_container_client(settings.cosmos_runs_container)
        self._artifacts = database.get_container_client(settings.cosmos_artifacts_container)

    def create_run(self, document: dict[str, Any]) -> dict[str, Any]:
        return self._runs.create_item(document)

    def upsert_run(self, document: dict[str, Any]) -> dict[str, Any]:
        return self._runs.upsert_item(document)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        query = 'SELECT * FROM c WHERE c.runId = @runId'
        items = list(self._runs.query_items(
            query=query,
            parameters=[{'name': '@runId', 'value': run_id}],
            enable_cross_partition_query=True,
        ))
        return items[0] if items else None

    def list_runs(self, *, project_name: str | None = None, dataset_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        filters: list[str] = []
        parameters: list[dict[str, Any]] = []

        if project_name:
            filters.append('c.projectName = @projectName')
            parameters.append({'name': '@projectName', 'value': project_name})
        if dataset_id:
            filters.append('c.datasetId = @datasetId')
            parameters.append({'name': '@datasetId', 'value': dataset_id})
        if status:
            filters.append('c.status = @status')
            parameters.append({'name': '@status', 'value': status})

        query = 'SELECT * FROM c'
        if filters:
            query = f"{query} WHERE {' AND '.join(filters)}"
        query = f'{query} ORDER BY c.createdAt DESC'

        return list(self._runs.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        ))

    def create_artifact(self, document: dict[str, Any]) -> dict[str, Any]:
        return self._artifacts.create_item(document)

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        query = 'SELECT * FROM c WHERE c.runId = @runId ORDER BY c.createdAt DESC'
        return list(self._artifacts.query_items(
            query=query,
            parameters=[{'name': '@runId', 'value': run_id}],
            enable_cross_partition_query=True,
        ))

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        query = 'SELECT * FROM c WHERE c.artifactId = @artifactId'
        items = list(self._artifacts.query_items(
            query=query,
            parameters=[{'name': '@artifactId', 'value': artifact_id}],
            enable_cross_partition_query=True,
        ))
        return items[0] if items else None