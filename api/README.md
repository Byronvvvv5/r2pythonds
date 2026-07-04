# Azure API Module

This directory contains the first Azure Functions API module for `r2pythonds`.

## Endpoints

- `POST /api/runs`
- `POST /api/runs/{runId}/inputs`
- `POST /api/runs/{runId}/start`
- `GET /api/runs/{runId}`
- `GET /api/runs`
- `GET /api/runs/{runId}/artifacts`
- `GET /api/artifacts/{artifactId}/download`
- `GET /api/health`

## Local development

1. Copy `local.settings.example.json` to `local.settings.json` and fill in values.
2. Install dependencies from `requirements.txt`.
3. Run Azure Functions Core Tools from the `api/` directory.

## Notes

- The API is intentionally thin. It persists metadata, stores input artifacts, and triggers the batch runner.
- The actual data pipeline still belongs in the separate runner module.