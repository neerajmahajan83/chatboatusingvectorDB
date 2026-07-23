FRS Flow
=========

Overview
--------
This document describes the functional request-and-response flow (FRS Flow) used by the chat service in this repository. It explains how user queries are handled, how records are searched, and how external fallback answers are persisted for future use.

Components
----------
- HTTP API: The Flask application exposes endpoints for health checks (`/`) and a chat endpoint (`/chat`).
- Records store: `record.json` contains question/answer pairs used for local retrieval.
- Retrieval logic: Incoming queries are matched against local records using simple substring matching.
- Remote fallback: If no local match is found, the service queries a remote provider for an answer.
- Persistence: Helpful remote answers are appended to `record.json` so future queries can be served locally.

Request flow
-----------
1. Client sends JSON POST to `/chat` with `{"message": "..."}`.
2. The service validates the input and ensures `record.json` is loaded.
3. The service attempts to find matching records via substring search on stored questions and answers.
4. If matches are found, one or more matching answers are returned immediately.
5. If no local match is found, the service queries a remote provider for an answer.
6. If the remote provider returns a useful answer, it is returned to the client and appended to `record.json`.
7. If nothing suitable is found, a standard fallback message is returned.

Persistence rules
-----------------
- Only non-empty, non-fallback answers are persisted.
- Duplicate questions (case-insensitive exact match) are not appended.
- New entries are given an incremental integer `id` and appended to `record.json` in place.

Notes for operators
-------------------
- Keep `COHERE_API_KEY` set in environment variables to enable remote fallback queries.
- The `record.json` file should be human-editable and is stored alongside the application.
- For production use, consider replacing the flat JSON store with a small database and adding authentication for the API.

Troubleshooting
---------------
- If responses are unexpectedly absent, check that `record.json` is readable and that the remote provider credentials are present.
- For debugging, check the application logs for messages indicating persistence or remote query failures.
