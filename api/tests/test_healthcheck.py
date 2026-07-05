import csv
import io
import json
from unittest.mock import patch, MagicMock

import pytest

from api.function_app import transform_run

@patch("function_app.DefaultAzureCredential")
@patch("function_app.cosmos_client")
@patch("function_app.blob_client")
def test_healthcheck_writes_expected_paths(mock_blob_client, mock_cosmos_client, mock_credential):
    sample_csv = "id,value,note\nhc-001,42,smoke test input\n"
    mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = (
        sample_csv.encode("utf-8")
    )

    req = MagicMock(get_json=lambda: {
        "projectName": "r2pythonds",
        "datasetId": "smoke-test-ds",
        "requestedBy": "smoke-test",
    })

    response = transform_run(req)

    assert response.status_code == 200

    upload_calls = [c for c in mock_blob_client.get_blob_client.call_args_list if len(c.args) > 1]
    output_call = upload_calls[-1]
    assert "output" in output_call.args[1]
    assert output_call.args[1].endswith("result.csv")


@patch("function_app.DefaultAzureCredential")
@patch("function_app.cosmos_client")
@patch("function_app.blob_client")
def test_healthcheck_transforms_csv_rows(mock_blob_client, mock_cosmos_client, mock_credential):
    sample_csv = "id,value,note\nhc-001,42,smoke test input\n"
    mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = (
        sample_csv.encode("utf-8")
    )

    upload_mock = mock_blob_client.get_blob_client.return_value.upload_blob
    req = MagicMock(get_json=lambda: {"projectName": "r2pythonds", "datasetId": "smoke-test-ds"})

    transform_run(req)

    uploaded_bytes = upload_mock.call_args.args[0]
    reader = csv.DictReader(io.StringIO(uploaded_bytes.decode("utf-8")))
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["id"] == "hc-001"
    assert rows[0]["value"] == "84"
    assert "processed_at" in rows[0]


@patch("function_app.DefaultAzureCredential")
@patch("function_app.cosmos_client")
@patch("function_app.blob_client")
def test_healthcheck_writes_run_and_artifact_documents(mock_blob_client, mock_cosmos_client, mock_credential):
    sample_csv = "id,value,note\nhc-001,42,smoke test input\n"
    mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = (
        sample_csv.encode("utf-8")
    )

    runs_container = MagicMock()
    artifacts_container = MagicMock()

    def get_container_client(name):
        return {"runs": runs_container, "artifacts": artifacts_container}[name]

    mock_cosmos_client.get_database_client.return_value.get_container_client.side_effect = get_container_client

    req = MagicMock(get_json=lambda: {"projectName": "r2pythonds", "datasetId": "smoke-test-ds"})

    response = transform_run(req)
    body = json.loads(response.get_body())

    assert body["status"] == "completed"
    assert len(body["outputArtifactIds"]) == 1

    runs_container.upsert_item.assert_called_once()
    artifacts_container.upsert_item.assert_called_once()

    upserted_artifact = artifacts_container.upsert_item.call_args.args[0]
    assert upserted_artifact["blobContainer"] == "processed-output"
    assert upserted_artifact["contentType"] == "text/csv"
    assert upserted_artifact["blobPath"].endswith("result.csv")


@patch("function_app.DefaultAzureCredential")
@patch("function_app.cosmos_client")
@patch("function_app.blob_client")
def test_healthcheck_missing_value_column_raises(mock_blob_client, mock_cosmos_client, mock_credential):
    bad_csv = "id,note\nhc-001,missing value column\n"
    mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = (
        bad_csv.encode("utf-8")
    )

    req = MagicMock(get_json=lambda: {"projectName": "r2pythonds", "datasetId": "smoke-test-ds"})

    with pytest.raises(KeyError):
        transform_run(req)