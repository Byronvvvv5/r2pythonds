import json
from typing import Any

import azure.functions as func


def json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload, default=str),
        status_code=status_code,
        mimetype='application/json',
    )


def error_response(message: str, status_code: int = 400, *, details: Any = None) -> func.HttpResponse:
    payload = {'error': message}
    if details is not None:
        payload['details'] = details
    return json_response(payload, status_code=status_code)