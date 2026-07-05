from api.shared.models import build_input_blob_path, build_output_prefix, finalize_run_document, new_run_document

def test_build_input_blob_path_is_deterministic():
    path = build_input_blob_path('SYN', 'Batch 01', 'run-123', 'test file.csv')
    assert path == 'project/syn/dataset/batch-01/run/run-123/input/test file.csv'


def test_build_output_prefix_matches_contract():
    prefix = build_output_prefix('Migration', 'Demo Set', 'run-123')
    assert prefix == 'project/migration/dataset/demo-set/run/run-123/output'


def test_run_document_gets_run_id():
    document = finalize_run_document(new_run_document({'projectName': 'SYN', 'datasetId': 'demo'}))
    assert document['runId'] == document['id']
    assert document['status'] == 'created'