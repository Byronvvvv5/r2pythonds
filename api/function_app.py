import azure.functions as func

from shared.blob_store import BlobStore
from shared.config import ConfigError, get_settings
from shared.cosmos_store import CosmosStore
from shared.job_runner import ContainerAppsJobRunner
from shared.models import build_input_prefix, build_output_prefix, finalize_run_document, new_artifact_document, new_run_document, sanitize_filename, utc_now_iso
from shared.responses import error_response, json_response


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _get_services() -> tuple[CosmosStore, BlobStore, ContainerAppsJobRunner]:
    settings = get_settings()
    return CosmosStore(settings), BlobStore(settings), ContainerAppsJobRunner(settings)


def _parse_json(req: func.HttpRequest) -> dict:
    try:
        return req.get_json()
    except ValueError as exc:
        raise ValueError('Request body must be valid JSON.') from exc


@app.route(route='runs', methods=['POST'])
def create_run(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = _parse_json(req)
        if not payload.get('projectName') or not payload.get('datasetId'):
            return error_response('projectName and datasetId are required.', 400)

        cosmos_store, _, _ = _get_services()
        run_document = finalize_run_document(new_run_document(payload))
        created = cosmos_store.create_run(run_document)
        response = {
            'runId': created['runId'],
            'status': created['status'],
            'projectName': created['projectName'],
            'datasetId': created['datasetId'],
            'links': {
                'self': f"/api/runs/{created['runId']}",
                'uploadInputs': f"/api/runs/{created['runId']}/inputs",
                'start': f"/api/runs/{created['runId']}/start",
                'artifacts': f"/api/runs/{created['runId']}/artifacts",
            },
        }
        return json_response(response, 201)
    except ConfigError as exc:
        return error_response(str(exc), 500)
    except ValueError as exc:
        return error_response(str(exc), 400)


@app.route(route='runs/{run_id}/inputs', methods=['POST'])
def upload_input(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get('run_id')

    try:
        cosmos_store, blob_store, _ = _get_services()
        run_document = cosmos_store.get_run(run_id)
        if not run_document:
            return error_response('Run not found.', 404)

        filename = req.params.get('filename') or req.headers.get('x-file-name')
        if not filename:
            return error_response('filename query parameter or x-file-name header is required.', 400)

        body = req.get_body()
        if not body:
            return error_response('Request body must contain file content.', 400)

        content_type = req.headers.get('content-type', 'application/octet-stream')
        cleaned_filename = sanitize_filename(filename)
        blob_container, blob_path = blob_store.upload_input_blob(
            project_name=run_document['projectName'],
            dataset_id=run_document['datasetId'],
            run_id=run_document['runId'],
            filename=cleaned_filename,
            body=body,
            content_type=content_type,
        )

        artifact_document = new_artifact_document(
            run_document=run_document,
            direction='input',
            blob_container=blob_container,
            blob_path=blob_path,
            logical_name=req.params.get('logicalName', cleaned_filename),
            content_type=content_type,
            stage_name='input',
            artifact_type='file',
        )
        cosmos_store.create_artifact(artifact_document)

        run_document['inputArtifactIds'] = sorted(set(run_document.get('inputArtifactIds', []) + [artifact_document['artifactId']]))
        run_document['updatedAt'] = utc_now_iso()
        cosmos_store.upsert_run(run_document)

        return json_response({
            'artifactId': artifact_document['artifactId'],
            'runId': run_document['runId'],
            'blobContainer': blob_container,
            'blobPath': blob_path,
        }, 201)
    except FileExistsError:
        return error_response('A file with the same blob path already exists for this run.', 409)
    except ConfigError as exc:
        return error_response(str(exc), 500)


@app.route(route='runs/{run_id}/start', methods=['POST'])
def start_run(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get('run_id')

    try:
        cosmos_store, _, job_runner = _get_services()
        run_document = cosmos_store.get_run(run_id)
        if not run_document:
            return error_response('Run not found.', 404)
        if run_document['status'] not in {'created', 'failed'}:
            return error_response(f"Run is not startable from status {run_document['status']}.", 409)

        input_prefix = build_input_prefix(
            run_document['projectName'],
            run_document['datasetId'],
            run_document['runId'],
        )

        execution = job_runner.trigger_run(run_document=run_document, input_prefix=input_prefix)
        run_document['status'] = 'submitted'
        run_document['submittedAt'] = utc_now_iso()
        run_document['updatedAt'] = run_document['submittedAt']
        run_document['execution'] = execution
        cosmos_store.upsert_run(run_document)

        return json_response({
            'runId': run_document['runId'],
            'status': run_document['status'],
            'execution': execution,
            'outputPrefix': build_output_prefix(run_document['projectName'], run_document['datasetId'], run_document['runId']),
        }, 202)
    except ConfigError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response('Failed to start container job.', 502, details=str(exc))


@app.route(route='runs/{run_id}', methods=['GET'])
def get_run(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get('run_id')

    try:
        cosmos_store, _, _ = _get_services()
        run_document = cosmos_store.get_run(run_id)
        if not run_document:
            return error_response('Run not found.', 404)
        return json_response(run_document)
    except ConfigError as exc:
        return error_response(str(exc), 500)


@app.route(route='runs', methods=['GET'])
def list_runs(req: func.HttpRequest) -> func.HttpResponse:
    try:
        cosmos_store, _, _ = _get_services()
        runs = cosmos_store.list_runs(
            project_name=req.params.get('projectName'),
            dataset_id=req.params.get('datasetId'),
            status=req.params.get('status'),
        )
        return json_response({'count': len(runs), 'items': runs})
    except ConfigError as exc:
        return error_response(str(exc), 500)


@app.route(route='runs/{run_id}/artifacts', methods=['GET'])
def list_artifacts(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get('run_id')

    try:
        cosmos_store, _, _ = _get_services()
        artifacts = cosmos_store.list_artifacts(run_id)
        return json_response({'count': len(artifacts), 'items': artifacts})
    except ConfigError as exc:
        return error_response(str(exc), 500)


@app.route(route='artifacts/{artifact_id}/download', methods=['GET'])
def get_artifact_download(req: func.HttpRequest) -> func.HttpResponse:
    artifact_id = req.route_params.get('artifact_id')

    try:
        cosmos_store, blob_store, _ = _get_services()
        artifact = cosmos_store.get_artifact(artifact_id)
        if not artifact:
            return error_response('Artifact not found.', 404)

        download_url, expires_at = blob_store.generate_download_url(
            blob_container=artifact['blobContainer'],
            blob_path=artifact['blobPath'],
        )
        return json_response({
            'artifactId': artifact['artifactId'],
            'downloadUrl': download_url,
            'expiresAt': expires_at,
        })
    except ConfigError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response('Failed to generate artifact download URL.', 502, details=str(exc))


@app.route(route='health', methods=['GET'])
def health(_: func.HttpRequest) -> func.HttpResponse:
    try:
        settings = get_settings()
        return json_response({
            'status': 'ok',
            'storageAccount': settings.storage_account_name,
            'cosmosDatabase': settings.cosmos_database_name,
            'jobName': settings.container_job_name,
        })
    except ConfigError as exc:
        return error_response(str(exc), 500)