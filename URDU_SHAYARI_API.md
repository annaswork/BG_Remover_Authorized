# Urdu Shayari API

HTTP API for Urdu poet personas, streamed poetry, and chat persistence. All routes are mounted under **`/api/urdu-shayari`**.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **MongoDB** | Same cluster as the rest of the app (`MONGODB_URL`). Chat and poetry completions are stored in the database named by **`URDU_SHAYARI_DATABASE`** (default `Urdu_Shayari`; override in `.env`). |
| **OpenAI** | **`OPENAI_API_KEY`** must be set in the environment. If it is missing, endpoints that call OpenAI return **503** with a clear message. |
| **API key** | Every endpoint below requires a valid app API key in the **`X-API-Key`** header (same keys as background remover — issued via `POST /api/auth/generate-key` and stored in the authorization database). |

---

## Authentication

Send the header on every request:

```http
X-API-Key: <your-api-key>
```

Unauthorized or invalid keys receive **401** (handled by shared auth dependencies).

---

## Overview

| Method | Path | Response type |
|--------|------|----------------|
| `POST` | `/api/urdu-shayari/ai-conversation` | JSON |
| `POST` | `/api/urdu-shayari/stream/ai-conversation` | `text/plain` stream |
| `GET` | `/api/urdu-shayari/stream/poetry-by-topic` | `text/plain` stream |
| `GET` | `/api/urdu-shayari/stream/poetry-by-type` | `text/plain` stream |
| `GET` | `/api/urdu-shayari/chat-history` | JSON |
| `DELETE` | `/api/urdu-shayari/chat-history` | JSON |

---

## `POST /api/urdu-shayari/ai-conversation`

Non-streaming chat with a persona. The server runs model and translation work in a worker thread (concurrency is limited by an internal semaphore).

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `character` | Yes | One of: `Urdu Scholar`, `Shayar`, `Dost`, `Competitor`, `Ustad` (Ustad is normalized internally to Urdu Scholar for role selection). |
| `username` | Yes | Client-supplied user id for persistence. |
| `name` | No | Optional display name (may be translated for prompts). |
| `gender` | No | Optional (may be translated). |
| `age` | No | Optional; passed through as provided. |

### Request body (`application/json`)

```json
{
  "prompt": "Your message to the character."
}
```

### Success response (`200`)

```json
{
  "response": "<assistant reply as string, or empty array on failure>"
}
```

On model or pipeline failure, `response` may be an empty array `[]` with status **200** (same shape as the existing controller).

### Errors

| Status | When |
|--------|------|
| **503** | OpenAI not configured (`OPENAI_API_KEY` unset). |

---

## `POST /api/urdu-shayari/stream/ai-conversation`

Same persona, translation, and persistence rules as **`ai-conversation`**, but the assistant reply is streamed as **UTF-8 plain text** chunks. After the stream completes successfully, the full reply is saved to MongoDB like the non-streaming path.

### Query parameters

Same as **`POST /ai-conversation`**: `character`, `username`, optional `name`, `gender`, `age`.

### Request body

Same JSON: `{ "prompt": "..." }`.

### Success response (**200**)

- **`Content-Type`:** `text/plain; charset=utf-8`
- **Body:** incremental text (OpenAI chat completion deltas). Clients should read the body with streaming HTTP (e.g. `fetch` + `ReadableStream`).

### Errors

| Status | When |
|--------|------|
| **503** | OpenAI not configured. |

Errors before streaming starts are JSON when FastAPI returns them; once **200** and streaming begins, failures may truncate the stream.

---

## `GET /api/urdu-shayari/stream/poetry-by-topic`

Streams generated poetry for a **topic** (Urdu-oriented prompts defined in app config).

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `poetry_topic` | Yes | Topic text (e.g. a theme in Urdu or Roman script). |
| `username` | Yes | Used for logging / persistence metadata in the poetry pipeline. |

### Success response (**200**)

- **`Content-Type`:** `text/plain; charset=utf-8`
- **Body:** streamed text (line-oriented formatting may appear depending on model output parsing).

### Errors

| Status | When |
|--------|------|
| **503** | OpenAI not configured. |

---

## `GET /api/urdu-shayari/stream/poetry-by-type`

Same as poetry-by-topic, but keyed by **poetry type** (e.g. غزل).

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `poetry_type` | Yes | Type label. |
| `username` | No | Optional; defaults to empty string internally if omitted. |

### Success response

Same as poetry-by-topic: **200**, `text/plain; charset=utf-8`, streamed body.

### Errors

| Status | When |
|--------|------|
| **503** | OpenAI not configured. |

---

## `GET /api/urdu-shayari/chat-history`

Returns stored documents for a user, filtered by **one** of: poetry topic, poetry type, or character conversation.

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `username` | Yes | User id. |
| `poetry_topic` | One of three filters required | Match topic history. |
| `poetry_type` | (see above) | Match type history. |
| `character` | (see above) | Match AI conversation history for that character. |
| `name` | No | Refines character-mode query (`character_name` in DB). |
| `gender` | No | Refines character-mode query. |

You must supply **at least one** of `poetry_topic`, `poetry_type`, or `character`. Otherwise the API returns **400** with:

```json
{
  "detail": "Provide at least one of: poetry_topic, poetry_type, or character"
}
```

### Success response (`200`)

```json
{
  "items": [
    {
      "_id": "<stringified ObjectId>",
      "...": "additional fields depend on collection (by_topic / by_type / ai_conversation)"
    }
  ]
}
```

Items are returned in reverse chronological order as implemented in the controller (newest inserted at the front of the list).

---

## `DELETE /api/urdu-shayari/chat-history`

Deletes **character-mode** conversation documents for a user (not topic/type collections).

### Query parameters

| Name | Required | Description |
|------|----------|-------------|
| `username` | Yes | User id. |
| `character` | Yes | Character key as stored for conversations. |
| `name` | No | Narrows delete to `character_name`. |
| `gender` | No | Narrows delete to `gender`. |

### Success response (`200`)

```json
{
  "info": "<human-readable summary including deleted count>",
  "flag": true
}
```

If required fields are missing internally, the controller may return `flag: false` and an `info` message (still **200** unless the router is changed).

---

## MongoDB layout (reference)

Configured in **`database/database_config.py`** against **`URDU_SHAYARI_DATABASE`**:

| Collection | Typical use |
|------------|-------------|
| `shayari_by_topics` | Poetry by topic |
| `shayari_by_types` | Poetry by type |
| `ai_conversation` | Persona chat (`ai-conversation` and `stream/ai-conversation`) |

---

## Web UI

The main dashboard (**`GET /`**) includes an **Urdu Shayari AI** page: API key field, non-streaming send, streaming character reply, streamed poetry by topic/type, and chat history load/delete helpers. Behavior matches the routes above.

---

## OpenAPI

Interactive docs list the same operations under the **`urdu-shayari`** tag:

- **`/docs`** (Swagger UI)
- **`/redoc`** (ReDoc)
