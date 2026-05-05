# Mobile API Integration Guide

This document is for mobile app developers integrating with the BG Remover backend.

## Base URL

- Local/dev example: `http://172.16.0.94:8000`
- Swagger docs: `http://<host>:<port>/docs`

## Authentication Headers

Two different keys are used by this backend:

- `X-API-Key`: App/client key used by mobile apps for image-processing APIs.
- `X-Admin-Key`: Admin key for key-management and analytics/admin operations (should **not** be shipped inside mobile apps).

### Header Format

Send keys exactly as plain header values (no `Bearer` prefix):

```http
X-API-Key: <api_key_value>
X-Admin-Key: <admin_api_key_value>
```

## API Key Value Format

`X-API-Key` values in this project are stored/validated as:

- 64-character lowercase hexadecimal string
- generated using `HMAC-SHA256(input_key, SECRET_KEY)`

Example shape:

```text
my_admin_key_2026_prod                           <-- example admin key (env-defined, arbitrary format)
7f83b1657ff1fc53b92dc18148a1d65dfa13514a3f6d2f8a2d5a6f8a51b5f7d1   <-- example API key shape (64 hex chars)
```

Notes:

- Mobile clients should treat keys as opaque strings and never transform them.
- API key comparison is exact-match; any missing/extra character fails auth.
- `401` means missing key header; `403` means key provided but invalid/inactive.

---

## Endpoints Used by Mobile Apps

## 1) Health Check

- **Method:** `GET`
- **Path:** `/api/bg-remover/`
- **Auth:** None
- **Response:**

```json
{
  "message": "BG Remover API is running"
}
```

## 2) Remove Background

- **Method:** `POST`
- **Path:** `/api/bg-remover/remove`
- **Auth:** `X-API-Key` required
- **Content-Type:** `multipart/form-data`

### Request Body

- `file` (required): image file upload

### Success Response (200)

```json
{
  "message": "Background removed successfully",
  "image_url": "http://<host>:<port>/static/results/<filename>.webp",
  "filename": "<filename>.webp"
}
```

### Common Error Responses

```json
{
  "detail": "API key missing. Provide it via the X-API-Key header."
}
```

```json
{
  "detail": "Invalid or inactive API key."
}
```

## 3) Face Crop

- **Method:** `POST`
- **Path(s):** `/api/face_detect/` or `/api/face_detect/face-crop`
- **Auth:** `X-API-Key` required
- **Content-Type:** `multipart/form-data`

### Request Body

- `file` (required): image file
- `width` (required, number, `> 0`)
- `height` (required, number, `> 0`)
- `unit` (required, string): one of `px`, `inch`, `mm`
- `dpi` (optional, integer, default `96`, minimum `1`)

### Success Response

Response is JSON with `message` and processed output metadata/URL (same response envelope style as other image routes).

## 4) Face Swap

- **Method:** `POST`
- **Path:** `/api/face_detect/swap`
- **Auth:** `X-API-Key` required
- **Content-Type:** `multipart/form-data`

### Request Body

- `source` (required): source image, must contain exactly one face
- `target` (required): target image, can contain one or more faces

### Success Response

Response is JSON with `message` and processed output metadata/URL (same response envelope style as other image routes).

---

## Admin/Backoffice Endpoints (Not for Public Mobile Clients)

These endpoints require `X-Admin-Key`.

- `POST /api/auth/generate-key`
- `GET /api/auth/keys`
- `DELETE /api/auth/revoke-key?api_key=<key>`
- `PATCH /api/auth/restore-key?api_key=<key>`
- `GET /api/analytics/*`
- `DELETE /api/analytics/cleanup`

## `POST /api/auth/generate-key` Request Format

```json
{
  "app_name": "MyMobileApp",
  "secret_key": "optional-custom-input"
}
```

If `secret_key` is omitted, server generates a random base key before HMAC signing.

---

## Mobile Implementation Rules

- Always send `X-API-Key` on protected endpoints.
- Never hardcode `X-Admin-Key` in app binaries.
- Store `X-API-Key` in secure storage (Keychain/Keystore equivalent).
- Use HTTPS in production.
- Upload images as multipart binary, not base64 JSON.
- Treat any non-2xx response as failure and surface `detail` message.

## Quick cURL Examples

### Background Remove

```bash
curl -X POST "http://172.16.0.94:8000/api/bg-remover/remove" \
  -H "X-API-Key: <your_api_key>" \
  -F "file=@/path/to/image.jpg"
```

### Face Crop

```bash
curl -X POST "http://172.16.0.94:8000/api/face_detect/face-crop" \
  -H "X-API-Key: <your_api_key>" \
  -F "file=@/path/to/image.jpg" \
  -F "width=600" \
  -F "height=800" \
  -F "unit=px" \
  -F "dpi=96"
```

### Face Swap

```bash
curl -X POST "http://172.16.0.94:8000/api/face_detect/swap" \
  -H "X-API-Key: <your_api_key>" \
  -F "source=@/path/to/source.jpg" \
  -F "target=@/path/to/target.jpg"
```
