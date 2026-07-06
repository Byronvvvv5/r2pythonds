import csv
import io
import json
from unittest.mock import patch, MagicMock

from function_app import transform_run


@patch("function_app.get_db_name", return_value="testdb")
@patch("function_app.get_cosmos_client")
@patch("function_app.get_blob_client")
def test_transform_run_writes_expected_output(mock_get_blob_client, mock_get_cosmos_client, mock_get_db_name):
    blob_client = MagicMock()
    cosmos_client = MagicMock()

    mock_get_blob_client.return_value = blob_client
    mock_get_cosmos_client.return_value = cosmos_client

    run_doc = {
        "id": "run-123",
        "runId": "run-123",
        "projectName": "r2pythonds",
        "datasetId": "smoke-test-ds",
        "inputArtifactIds": ["artifact-001"],
        "outputArtifactIds": [],
        "status": "awaiting_input",
    }

    input_artifact = {
        "id": "artifact-001",
        "artifactId": "artifact-001",
        "runId": "run-123",
        "blobContainer": "raw-input",
        "blobPath": "project/r2pythonds/dataset/smoke-test-ds/run/run-123/input/sample_healthcheck.csv",
        "contentType": "text/csv",
    }

    runs_container = MagicMock()
    artifacts_container = MagicMock()

    def get_container_client(name):
        return {"runs": runs_container, "artifacts": artifacts_container}[name]

    cosmos_client.get_database_client.return_value.get_container_client.side_effect = get_container_client
    runs_container.read_item.return_value = run_doc
    artifacts_container.read_item.return_value = input_artifact

    sample_csv = "id,value,note\nhc-001,42,smoke test input\n"
    download_blob = MagicMock()
    download_blob.readall.return_value = sample_csv.encode("utf-8")

    input_blob = MagicMock()
    input_blob.download_blob.return_value = download_blob

    output_blob = MagicMock()

    def get_blob(container, path):
        if container == "raw-input":
            return input_blob
        return output_blob

    blob_client.get_blob_client.side_effect = get_blob

    req = MagicMock()
    req.route_params = {"run_id": "run-123"}

    response = transform_run(req)

    assert response.status_code == 200

    uploaded_bytes = output_blob.upload_blob.call_args.args[0]
    reader = csv.DictReader(io.StringIO(uploaded_bytes.decode("utf-8")))
    rows = list(reader)

    assert rows[0]["value"] == "84"
    assert "processed_at" in rows[0]

    artifacts_container.upsert_item.assert_called_once()
    runs_container.upsert_item.assert_called_once()

    body = json.loads(response.get_body())
    assert body["status"] == "completed"