import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def generate_run_id() -> str:
    return f'run-{uuid4().hex[:12]}'


def generate_artifact_id() -> str:
    return f'artifact-{uuid4().hex[:12]}'


def normalize_segment(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r'[^a-z0-9._-]+', '-', lowered)
    return normalized.strip('-') or 'unknown'


def sanitize_filename(filename: str) -> str:
    cleaned = filename.split('/')[-1].split('\\')[-1].strip()
    return cleaned or 'uploaded.bin'


def build_input_blob_path(project_name: str, dataset_id: str, run_id: str, filename: str) -> str:
    return '/'.join([
        'project',
        normalize_segment(project_name),
        'dataset',
        normalize_segment(dataset_id),
        'run',
        run_id,
        'input',
        sanitize_filename(filename),
    ])


def build_input_prefix(project_name: str, dataset_id: str, run_id: str) -> str:
    return '/'.join([
        'project',
        normalize_segment(project_name),
        'dataset',
        normalize_segment(dataset_id),
        'run',
        run_id,
        'input',
    ])


def build_output_prefix(project_name: str, dataset_id: str, run_id: str) -> str:
    return '/'.join([
        'project',
        normalize_segment(project_name),
        'dataset',
        normalize_segment(dataset_id),
        'run',
        run_id,
        'output',
    ])


def new_run_document(payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = utc_now_iso()
    project_name = str(payload['projectName']).strip()
    dataset_id = str(payload['datasetId']).strip()
    return {
        'id': generate_run_id(),
        'runId': None,
        'projectName': project_name,
        'datasetId': dataset_id,
        'requestedBy': payload.get('requestedBy', 'unknown'),
        'parameters': payload.get('parameters', {}),
        'status': 'created',
        'inputArtifactIds': [],
        'outputArtifactIds': [],
        'createdAt': timestamp,
        'updatedAt': timestamp,
        'submittedAt': None,
        'startedAt': None,
        'completedAt': None,
        'errorSummary': None,
        'execution': None,
    }


def finalize_run_document(run_document: dict[str, Any]) -> dict[str, Any]:
    run_document['runId'] = run_document['id']
    return run_document


def new_artifact_document(
    *,
    run_document: dict[str, Any],
    direction: str,
    blob_container: str,
    blob_path: str,
    logical_name: str,
    content_type: str,
    stage_name: str,
    artifact_type: str,
) -> dict[str, Any]:
    timestamp = utc_now_iso()
    artifact_id = generate_artifact_id()
    return {
        'id': artifact_id,
        'artifactId': artifact_id,
        'runId': run_document['runId'],
        'projectName': run_document['projectName'],
        'datasetId': run_document['datasetId'],
        'direction': direction,
        'stageName': stage_name,
        'artifactType': artifact_type,
        'logicalName': logical_name,
        'blobContainer': blob_container,
        'blobPath': blob_path,
        'contentType': content_type,
        'createdAt': timestamp,
    }