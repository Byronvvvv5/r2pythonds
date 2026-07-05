import os
import io
import csv
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from shared import models

app = func.FunctionApp()
credential = DefaultAzureCredential()

STORAGE_ACCOUNT_URL = os.environ["STORAGE_ACCOUNT_URL"]
COSMOS_ENDPOINT = os.environ["COSMOS_DB_ENDPOINT"]
DB_NAME = os.environ["COSMOS_DB_DATABASE_NAME"]

blob_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=credential)

@app.route(route="runs/{run_id}/transform", methods=["POST"])
def transform_run(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get("run_id")
    db = cosmos_client.get_database_client(DB_NAME)
    runs_container = db.get_container_client("runs")
    artifacts_container = db.get_container_client("artifacts")

    run_doc = runs_container.read_item(item=run_id, partition_key=run_id)

    input_artifact_id = run_doc["inputArtifactIds"][0]
    input_artifact = artifacts_container.read_item(item=input_artifact_id, partition_key=run_id)

    input_blob = blob_client.get_blob_client(input_artifact["blobContainer"], input_artifact["blobPath"])
    raw_bytes = input_blob.download_blob().readall()
    reader = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8")))
    rows = list(reader)

    transformed_rows = []
    for row in rows:
        row["value"] = str(int(row["value"]) * 2)
        row["processed_at"] = models.utc_now_iso()
        transformed_rows.append(row)

    output_prefix = models.build_output_prefix(run_doc["projectName"], run_doc["datasetId"], run_id)
    output_path = f"{output_prefix}/result.csv"

    out_buffer = io.StringIO()
    fieldnames = list(transformed_rows[0].keys()) if transformed_rows else ["id", "value", "note", "processed_at"]
    writer = csv.DictWriter(out_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(transformed_rows)

    blob_client.get_blob_client("processed-output", output_path).upload_blob(
        out_buffer.getvalue().encode("utf-8"), overwrite=True
    )

    output_artifact = models.new_artifact_document(
        run_document=run_doc, direction="output", blob_container="processed-output",
        blob_path=output_path, logical_name="result.csv",
        content_type="text/csv", stage_name="transform", artifact_type="processed-output",
    )
    run_doc["outputArtifactIds"].append(output_artifact["artifactId"])
    run_doc["status"] = "completed"
    run_doc["completedAt"] = models.utc_now_iso()
    run_doc["updatedAt"] = models.utc_now_iso()

    runs_container.upsert_item(run_doc)
    artifacts_container.upsert_item(output_artifact)

    return func.HttpResponse(json.dumps(run_doc), mimetype="application/json", status_code=200)

@app.route(route="runs/{run_id}", methods=["GET"])
def get_run(req: func.HttpRequest) -> func.HttpResponse:
    run_id = req.route_params.get("run_id")
    db = cosmos_client.get_database_client(DB_NAME)
    run_doc = db.get_container_client("runs").read_item(item=run_id, partition_key=run_id)

    artifacts_container = db.get_container_client("artifacts")
    artifacts = [artifacts_container.read_item(item=aid, partition_key=run_id)
                 for aid in run_doc.get("outputArtifactIds", [])]

    outputs = []
    for artifact in artifacts:
        blob = blob_client.get_blob_client(artifact["blobContainer"], artifact["blobPath"])
        raw_bytes = blob.download_blob().readall()
        reader = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8")))
        outputs.append({"artifact": artifact, "content": list(reader)})

    return func.HttpResponse(json.dumps({"metadata": run_doc, "outputs": outputs}),
                              mimetype="application/json", status_code=200)

@app.route(route="runs", methods=["POST"])
def create_run(req: func.HttpRequest) -> func.HttpResponse:
    payload = req.get_json()
    run_doc = models.new_run_document(payload)
    run_doc = models.finalize_run_document(run_doc)
    run_id = run_doc["runId"]

    filename = payload.get("filename", "sample_healthcheck.csv")
    input_path = models.build_input_blob_path(
        run_doc["projectName"], run_doc["datasetId"], run_id, filename
    )

    input_artifact = models.new_artifact_document(
        run_document=run_doc, direction="input", blob_container="raw-input",
        blob_path=input_path, logical_name=filename,
        content_type="text/csv", stage_name="upload", artifact_type="raw-input",
    )
    run_doc["inputArtifactIds"].append(input_artifact["artifactId"])
    run_doc["status"] = "awaiting_input"
    run_doc["updatedAt"] = models.utc_now_iso()

    db = cosmos_client.get_database_client(DB_NAME)
    db.get_container_client("runs").upsert_item(run_doc)
    db.get_container_client("artifacts").upsert_item(input_artifact)

    return func.HttpResponse(
        json.dumps({"runId": run_id, "inputContainer": "raw-input", "inputPath": input_path, "status": run_doc["status"]}),
        mimetype="application/json", status_code=201,
    )