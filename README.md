# Background Remover API

A FastAPI-based background removal service with API key authorization, per-app analytics tracking, and a built-in web dashboard.

---

## Table of Contents

- [Project Structure](#project-structure)
- [File Explanations](#file-explanations)
- [Setup & Configuration](#setup--configuration)
- [Running the Server](#running-the-server)
- [API Routes](#api-routes)
  - [Pages](#pages)
  - [Background Remover](#background-remover)
  - [Authorization](#authorization)
  - [Analytics](#analytics)
- [Authentication](#authentication)
- [Web Dashboard](#web-dashboard)

---

## Project Structure

```
BG_Remover_Authorized/
│
├── app.py                        # App entry point — wires middleware, routers, lifespan
├── run.py                        # Starts uvicorn server
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (secrets, DB config)
│
├── config/
│   └── index.py                  # All app-wide constants and env variable loading
│
├── inits/
│   └── server_init.py            # FastAPI app initialization (CORS, static, templates, thread pool)
│
├── router/
│   ├── app_router.py             # BG remover + UI page routes
│   ├── auth_router.py            # API key management routes
│   └── analytics_router.py      # Analytics query routes
│
├── controller/
│   ├── app_controller.py         # Background removal logic (rembg + thread pool)
│   ├── auth_controller.py        # FastAPI dependencies: require_api_key, require_admin_key
│   └── analytics_controller.py  # Analytics CRUD (legacy, superseded by analytics/crud.py)
│
├── analytics/
│   ├── middleware.py             # Starlette middleware — records every API request
│   ├── crud.py                   # Async MongoDB queries for analytics data
│   ├── routes.py                 # Re-exports analytics router (compatibility shim)
│   ├── excluded_paths.py         # Paths excluded from analytics tracking
│   └── index.py                  # Lifespan context manager (DB connect/disconnect)
│
├── authorization/
│   └── index.py                  # API key generation, validation, revoke, restore logic
│
├── database/
│   ├── database_config.py        # MongoDB async client setup, DB getters
│   ├── database_funcs.py         # Re-exports DB functions (single import point)
│   ├── analytics_model.py        # Pydantic models: Analytics, AnalyticsSummary
│   ├── authorization_model.py    # Pydantic model: APIKey
│   └── index.py                  # Lifespan helper (alternative entry)
│
├── utils/
│   ├── preprocess_image.py       # Image reading, EXIF fix, CV2 conversion, filename generation
│   ├── postprocess_image.py      # Image saving and URL generation
│   └── functions.py              # General utility placeholder
│
├── templates/
│   └── index.html                # Single-page web dashboard (vanilla JS, Chart.js)
│
└── static/
    └── results/                  # Output directory for processed images
```

---

## File Explanations

### `app.py`
Main application file. Registers the lifespan (MongoDB connect/disconnect), attaches `AnalyticsMiddleware`, and includes all routers.

### `run.py`
Starts the uvicorn server using host/port from `config/index.py`. Run this to start the application.

### `config/index.py`
Central configuration. Loads `.env` and exposes all constants:
- `IP`, `PORT` — server bind address
- `MONGODB_URL`, `ANALYTICS_DATABASE`, `AUTHORIZATION_DATABASE` — database config
- `SECRET_KEY` — used to HMAC-sign generated API keys
- `ADMIN_API_KEY` — master key for admin-only operations
- `ANALYTICS_COLLECTION_NAME`, `AUTHORIZATION_COLLECTION_NAME` — MongoDB collection names
- `IMAGE_PATH`, `IMAGE_URL_PREFIX` — output file paths

### `inits/server_init.py`
Initializes the FastAPI app instance with title, description, version. Mounts `/static` and `/templates` directories. Configures CORS (all origins), registers a `ThreadPoolExecutor` for CPU-bound tasks, and enables HEIF image support via `pillow_heif`.

### `analytics/middleware.py`
Starlette `BaseHTTPMiddleware` that intercepts every non-excluded request. Records: HTTP method, path, status code, request/response sizes, total bandwidth, client IP, user agent, response time, and `app_name` (resolved by looking up the `X-API-Key` header against MongoDB). Stores records asynchronously using `asyncio.create_task` to avoid blocking responses.

### `analytics/excluded_paths.py`
List of path prefixes excluded from analytics tracking. Includes `/`, `/docs`, `/static`, `/api/analytics`, `/api/auth`, and others.

### `analytics/crud.py`
All async MongoDB operations for analytics:
- `create_analytics_record` — insert a new log entry
- `get_analytics_records` — paginated, filterable record fetch
- `count_analytics_records` — total count for pagination
- `get_analytics_summary` — aggregated totals (requests, bandwidth, response time, by method/status/endpoint)
- `get_bandwidth_stats` — detailed bandwidth aggregation
- `get_ip_request_stats` — requests grouped by IP, date, and path
- `get_distinct_app_names` — unique app names for filter dropdowns
- `get_distinct_status_codes` — unique status codes for filter dropdowns
- `delete_old_analytics` — purge records older than N days

### `authorization/index.py`
API key lifecycle management:
- `generate_api_key(app_name, secret_key)` — creates a new key. The base (custom or random) is HMAC-SHA256 signed with `SECRET_KEY` from `.env` before storage.
- `validate_api_key(api_key)` — looks up an active key in MongoDB
- `list_api_keys()` — returns all keys with the raw value masked
- `revoke_api_key(api_key)` — sets `is_active = False`
- `restore_api_key(api_key)` — sets `is_active = True`

### `controller/auth_controller.py`
FastAPI security dependencies:
- `require_api_key` — reads `X-API-Key` header, validates against MongoDB. Used on the BG removal endpoint.
- `require_admin_key` — reads `X-Admin-Key` header, compares against `ADMIN_API_KEY` from `.env`. Used on all auth management endpoints.

### `controller/app_controller.py`
Background removal logic. Reads the uploaded image, converts it to PNG bytes, runs `rembg.remove()` in the thread pool (non-blocking), saves the result as WebP to `static/results/`, and returns the public URL. The rembg session (`u2net` model) is loaded once at module import time to avoid per-request model loading overhead.

### `database/database_config.py`
Async MongoDB client using `motor`. Provides `connect_to_mongo()`, `close_mongo_connection()`, `get_analytics_db()`, and `get_authorization_db()`.

### `database/analytics_model.py`
Pydantic models for analytics data:
- `Analytics` — single request log record
- `AnalyticsSummary` — aggregated summary response

### `database/authorization_model.py`
Pydantic model `APIKey` with fields: `app_name`, `api_key`, `created_at`, `is_active`.

---

## Setup & Configuration

### 1. Install dependencies
```bash
pip install "rembg[cpu]"   # or rembg[gpu] for NVIDIA GPU
pip install -r requirements.txt
```

### 2. Configure `.env`
```env
MONGODB_URL=mongodb://localhost:27017
ANALYTICS_DATABASE=analytics
AUTHORIZATION_DATABASE=authorization
SECRET_KEY=your-secret-key-here
ADMIN_API_KEY=your-admin-key-here
```

### 3. MongoDB
Ensure MongoDB is running locally on port `27017`. Collections are created automatically on first use.

---

## Running the Server

```bash
python run.py
```

Server starts at `http://172.16.0.94:8000` (configure `IP` and `PORT` in `config/index.py`).

Interactive API docs available at:
- Swagger UI: `http://<host>:<port>/docs`
- ReDoc: `http://<host>:<port>/redoc`

---

## API Routes

### Pages

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the web dashboard UI |

---

### Background Remover

Base prefix: `/api/bg-remover`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/bg-remover/` | None | Health check — returns running status |
| `POST` | `/api/bg-remover/remove` | `X-API-Key` | Remove background from uploaded image |
| `DELETE` | `/api/bg-remover/clear-results` | None | Delete all files in `static/results/` |

#### `POST /api/bg-remover/remove`
**Headers:** `X-API-Key: <your-api-key>`  
**Body:** `multipart/form-data` with field `file` (image file)  
**Supported formats:** PNG, JPG, WEBP, HEIC  
**Response:**
```json
{
  "message": "Background removed successfully",
  "image_url": "http://host:port/static/results/filename.webp",
  "filename": "filename.webp"
}
```

#### `DELETE /api/bg-remover/clear-results`
No auth required. Intended for use with a scheduler.  
**Response:**
```json
{
  "message": "Cleared 42 item(s) from results folder.",
  "deleted": 42,
  "errors": []
}
```

---

### Authorization

Base prefix: `/api/auth`  
All endpoints require `X-Admin-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/generate-key` | Generate a new API key for an app |
| `GET` | `/api/auth/keys` | List all API keys (masked) |
| `DELETE` | `/api/auth/revoke-key` | Deactivate an API key |
| `PATCH` | `/api/auth/restore-key` | Re-activate a revoked API key |

#### `POST /api/auth/generate-key`
**Headers:** `X-Admin-Key: <admin-key>`  
**Body:**
```json
{
  "app_name": "MyApp",
  "secret_key": "optional-custom-base"
}
```
The final stored key is `HMAC-SHA256(secret_key or random, SECRET_KEY_from_env)`.  
**Response:**
```json
{
  "message": "API key generated successfully",
  "data": {
    "app_name": "MyApp",
    "api_key": "<64-char hex key>",
    "created_at": "2026-04-28T...",
    "is_active": true
  }
}
```

#### `GET /api/auth/keys`
**Headers:** `X-Admin-Key: <admin-key>`  
Returns all keys with the value masked to first 8 chars + `...`

#### `DELETE /api/auth/revoke-key?api_key=<key>`
**Headers:** `X-Admin-Key: <admin-key>`

#### `PATCH /api/auth/restore-key?api_key=<key>`
**Headers:** `X-Admin-Key: <admin-key>`

---

### Analytics

Base prefix: `/api/analytics`  
No authentication required on analytics endpoints.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/analytics/filters-meta` | Distinct app names and status codes for dropdowns |
| `GET` | `/api/analytics/` | Paginated request logs with filters |
| `GET` | `/api/analytics/summary` | Aggregated totals (requests, bandwidth, response time) |
| `GET` | `/api/analytics/bandwidth` | Detailed bandwidth statistics |
| `GET` | `/api/analytics/ip-stats` | Request counts grouped by IP, date, and path |
| `DELETE` | `/api/analytics/cleanup` | Delete records older than N days |

#### Common Query Parameters (supported by most endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `app_name` | string | Filter by app name (partial, case-insensitive) |
| `method` | string | Filter by HTTP method (`GET`, `POST`, etc.) |
| `status_code` | int | Filter by HTTP status code |
| `path` | string | Filter by request path (partial match) |
| `start_date` | string | Start of date range (`YYYY-MM-DD` or ISO format) |
| `end_date` | string | End of date range (`YYYY-MM-DD` or ISO format) |
| `days` | int | Shorthand for last N days (alternative to start/end date) |

#### `GET /api/analytics/`
Additional parameters: `skip` (default `0`), `limit` (default `100`, max `1000`)

#### `DELETE /api/analytics/cleanup`
Parameter: `days` (default `90`) — deletes records older than this many days.

---

## Authentication

The system uses two separate authentication layers:

### API Key (`X-API-Key`)
Required to call the background removal endpoint. Generated per-app via the admin panel or `POST /api/auth/generate-key`.

```
POST /api/bg-remover/remove
X-API-Key: <your-api-key>
```

### Admin Key (`X-Admin-Key`)
A single master key defined in `.env` as `ADMIN_API_KEY`. Required for all key management operations and the admin sections of the web dashboard.

```
POST /api/auth/generate-key
X-Admin-Key: <your-admin-key>
```

### Key Generation Security
API keys are not stored as-is. The input (custom or random) is signed with `HMAC-SHA256` using the server's `SECRET_KEY`:

```
stored_key = HMAC-SHA256(input_key, SECRET_KEY)
```

This means even if the database is compromised, keys cannot be forged without the server secret.

---

## Web Dashboard

Accessible at `http://<host>:<port>/`

### BG Remover (public)
- Paste your API key
- Drag & drop or click to upload an image
- Preview original and result side by side
- Download the processed image

### Authorization (admin only)
- Generate new API keys with optional custom secret
- Revoke or restore keys by pasting the full key
- View all registered keys with status and creation date

### Analytics (admin only)
- Summary cards: total requests, bandwidth, avg response time, unique IPs
- Line charts: requests per day, bandwidth per day
- Filterable log table with app name dropdown, status code dropdown, and date pickers
- Pagination (50 records per page)
- Cleanup old records

> Admin sections require entering the `ADMIN_API_KEY` via the Admin Login button in the sidebar. The key is held in memory only and cleared on page refresh.
