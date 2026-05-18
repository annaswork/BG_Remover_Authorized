# Object Remover API

AI-powered object removal using **LaMa** (Large Mask Inpainting) for seamless inpainting and **SAM** (Segment Anything Model) for intelligent segmentation.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [SAM Segmentation](#sam-segmentation)
  - [Inpaint (JSON)](#inpaint-json)
  - [Inpaint (File Upload)](#inpaint-file-upload)
  - [Clear Results](#clear-results)
- [Web UI Usage](#web-ui-usage)
- [Technical Details](#technical-details)
- [Error Handling](#error-handling)

---

## Overview

The Object Remover feature allows users to:

1. **Upload an image** containing unwanted objects
2. **Click on objects** to automatically segment them using SAM
3. **Remove objects** seamlessly using LaMa inpainting
4. **Download results** as high-quality WebP images

The entire pipeline is optimized for production use:
- Models loaded once at startup (no per-request overhead)
- CPU-intensive work runs in a thread pool (non-blocking async)
- Results saved to disk with public URLs
- Full integration with the existing analytics and authorization system

---

## Architecture

### Models

**LaMa (Large Mask Inpainting)**
- State-of-the-art inpainting model
- Fills masked regions with contextually appropriate content
- Loaded via IOPaint's `ModelManager`
- Supports multiple HD strategies (Original, Crop, Resize)

**SAM (Segment Anything Model)**
- Interactive segmentation from click points
- Automatically detects object boundaries
- Wrapped via IOPaint's `InteractiveSeg`
- Supports both SAM (original) and SAM2 (faster)

### Integration Points

```
┌─────────────────────────────────────────────────────────┐
│                     app.py                              │
│  (registers object_remover_router)                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              router/object_remover_router.py            │
│  (FastAPI routes with auth + validation)                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│          controller/object_remover_controller.py        │
│  (async handlers → offload to thread_pool)              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              inits/models_init.py                       │
│  (loads lama_model and sam_processor at startup)        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              utils/sam_process.py                       │
│  (SAMProcessor wrapper for segmentation)                │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

Add these variables to your `.env` file:

```env
# ── Object Remover Models ──
LAMA_ENABLE=true                    # Enable LaMa inpainting model
LAMA_MODEL_TYPE=lama                # Model type: "lama" (default)
SAM_ENABLE=true                     # Enable SAM segmentation model
SAM_MODEL_TYPE=sam                  # Model type: "sam" or "sam2"
OBJECT_REMOVER_DEVICE=cpu           # Device: "cpu" or "cuda"
```

### Model Download

Models are downloaded automatically by IOPaint on first use:
- **LaMa**: ~200MB (downloaded to IOPaint cache)
- **SAM**: ~350MB for SAM, ~150MB for SAM2 (downloaded to IOPaint cache)

No manual download required. The server will fetch models on startup if `LAMA_ENABLE=true` or `SAM_ENABLE=true`.

---

## API Endpoints

All endpoints (except health check) require **`X-API-Key`** header.

### Health Check

**`GET /api/object-remover/health`**

Returns the load status of both models.

**Response:**
```json
{
  "status": "ok",
  "lama_loaded": true,
  "sam_loaded": true
}
```

**No authentication required** — safe for admin dashboards.

---

### SAM Segmentation

**`POST /api/object-remover/sam`**

Generate a segmentation mask from user click points.

**Headers:**
```
X-API-Key: <your-api-key>
```

**Body (multipart/form-data):**
| Field | Type | Description |
|-------|------|-------------|
| `image` | file | Source image (JPEG, PNG, WEBP) |
| `points` | string | JSON array of click coordinates: `[{"x": 100, "y": 200}, ...]` |

**Response:**
```json
{
  "mask": "<base64-encoded PNG mask>"
}
```

The mask is a binary image (255 = foreground, 0 = background) encoded as base64 PNG.

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/object-remover/sam \
  -H "X-API-Key: your-key-here" \
  -F "image=@photo.jpg" \
  -F 'points=[{"x":213,"y":232},{"x":220,"y":240}]'
```

---

### Inpaint (JSON)

**`POST /api/object-remover/inpaint`**

Remove an object using base64-encoded image and mask.

**Headers:**
```
X-API-Key: <your-api-key>
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "image": "<base64 string>",
  "mask": "<base64 string>",
  "ldmSteps": 25,
  "hdStrategy": "Original",
  "hdStrategyCropMargin": 128,
  "hdStrategyCropTrigerSize": 800,
  "hdStrategyResizeLimit": 2048,
  "maskExpand": 10
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image` | string | *required* | Base64-encoded source image |
| `mask` | string | *required* | Base64-encoded mask (white = erase) |
| `ldmSteps` | int | 25 | Inpainting steps (10-100). More = better quality but slower |
| `hdStrategy` | string | "Original" | HD strategy: "Original", "Crop", or "Resize" |
| `hdStrategyCropMargin` | int | 128 | Crop margin for "Crop" strategy |
| `hdStrategyCropTrigerSize` | int | 800 | Trigger size for HD processing |
| `hdStrategyResizeLimit` | int | 2048 | Max resolution for "Resize" strategy |
| `maskExpand` | int | 10 | Expand mask by N pixels (helps with edges) |

**Response:**
```json
{
  "message": "Object removed successfully",
  "result_url": "http://host:port/static/object_remover_results/abc123.webp",
  "filename": "abc123.webp"
}
```

---

### Inpaint (File Upload)

**`POST /api/object-remover/inpaint-file`**

Remove an object using multipart file uploads.

**Headers:**
```
X-API-Key: <your-api-key>
```

**Body (multipart/form-data):**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `image` | file | *required* | Source image (JPEG, PNG, WEBP) |
| `mask` | file | *required* | B&W mask image (white = erase) |
| `ldmSteps` | int | 25 | Inpainting steps |
| `hdStrategy` | string | "Original" | HD strategy |
| `hdStrategyCropMargin` | int | 128 | Crop margin |
| `hdStrategyCropTrigerSize` | int | 800 | Trigger size |
| `hdStrategyResizeLimit` | int | 2048 | Resize limit |
| `maskExpand` | int | 10 | Mask expansion |

**Response:**
```json
{
  "message": "Object removed successfully",
  "result_url": "http://host:port/static/object_remover_results/abc123.webp",
  "filename": "abc123.webp"
}
```

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/object-remover/inpaint-file \
  -H "X-API-Key: your-key-here" \
  -F "image=@photo.jpg" \
  -F "mask=@mask.png" \
  -F "ldmSteps=30" \
  -F "maskExpand=15"
```

---

### Clear Results

**`DELETE /api/object-remover/clear-results`**

Delete all saved result images from the object remover results folder.

**Headers:**
```
X-API-Key: <your-api-key>
```

**Response:**
```json
{
  "message": "Cleared 42 file(s) from object remover results.",
  "deleted": 42,
  "errors": []
}
```

---

## Web UI Usage

The web dashboard provides a complete interactive workflow:

### Step 1: Upload Image
- Drag & drop or click to upload
- Supports PNG, JPG, WEBP

### Step 2: Click on Object
- Click on the object you want to remove
- Add multiple points for better accuracy
- Points are marked with green circles
- Click "Generate Mask" to run SAM segmentation

### Step 3: Review & Remove
- Preview the generated mask
- Adjust mask expansion (default: 10px)
- Adjust inpainting steps (default: 25)
- Click "Remove Object" to run LaMa inpainting

### Step 4: Download Result
- Compare before/after side-by-side
- Download result as WebP
- Start over to remove another object

---

## Technical Details

### Thread Pool Execution

All CPU/GPU-intensive work runs in the shared `thread_pool` from `server_init.py`:

```python
loop = asyncio.get_event_loop()
filename = await loop.run_in_executor(
    thread_pool, _run_inpaint,
    np_image, np_mask, alpha_channel, ...
)
```

This keeps the async event loop free for handling other requests.

### Image Processing Pipeline

1. **Input**: User uploads image + clicks points
2. **SAM**: Segments object from click points → binary mask
3. **Mask Expansion**: Dilates mask by N pixels (optional)
4. **LaMa**: Inpaints masked region → seamless result
5. **Output**: Saves as WebP with 90% quality

### File Storage

Results are saved to:
```
static/object_remover_results/<uuid>.webp
```

Public URL:
```
http://<host>:<port>/static/object_remover_results/<uuid>.webp
```

### Model Loading

Models are loaded once at startup in `inits/models_init.py`:

```python
if LAMA_ENABLE:
    lama_model = ModelManager(
        name=LAMA_MODEL_TYPE,
        device=OBJECT_REMOVER_DEVICE,
        ...
    )

if SAM_ENABLE:
    sam_processor = SAMProcessor(
        model_type=SAM_MODEL_TYPE,
        device=OBJECT_REMOVER_DEVICE,
    )
```

If a model fails to load, the server logs a warning and continues. The `/health` endpoint will report the model as not loaded.

---

## Error Handling

### Model Not Loaded

**Status:** `503 Service Unavailable`

```json
{
  "detail": "LaMa inpainting model is not loaded. Set LAMA_ENABLE=true in .env and restart the server."
}
```

**Solution:** Enable the model in `.env` and restart.

### Invalid Input

**Status:** `422 Unprocessable Entity`

```json
{
  "detail": "Request body must contain 'image' and 'mask' base64 fields."
}
```

**Solution:** Ensure all required fields are present and correctly formatted.

### Processing Error

**Status:** `400 Bad Request`

```json
{
  "detail": "Image size (1920, 1080) and mask size (800, 600) don't match."
}
```

**Solution:** Ensure image and mask have the same dimensions.

### Authentication Error

**Status:** `401 Unauthorized`

```json
{
  "detail": "Invalid or missing API key"
}
```

**Solution:** Provide a valid `X-API-Key` header.

---

## Performance Tips

### For Best Quality
- Use `ldmSteps=50` or higher
- Use `maskExpand=15-20` for cleaner edges
- Use `hdStrategy="Crop"` for large images

### For Speed
- Use `ldmSteps=15-20`
- Use `maskExpand=5-10`
- Use `hdStrategy="Original"`
- Use `SAM_MODEL_TYPE=sam2` (faster than original SAM)

### For Large Images
- Use `hdStrategy="Resize"` with `hdStrategyResizeLimit=2048`
- Or use `hdStrategy="Crop"` to process only the masked region

---

## Dependencies

The object remover requires these Python packages (already in `requirements.txt`):

```
iopaint>=1.3.0          # LaMa + SAM models
opencv-python>=4.8.0    # Image processing
numpy>=1.24.0           # Array operations
pillow>=10.0.0          # Image I/O
```

IOPaint automatically handles model downloads and provides a unified interface for both LaMa and SAM.

---

## Troubleshooting

### Models not loading

**Check logs:**
```
[Models Init] Loading LaMa model (lama) on cpu...
[Models Init] LaMa model loaded successfully
```

If you see warnings, ensure:
1. `LAMA_ENABLE=true` and `SAM_ENABLE=true` in `.env`
2. Internet connection available (for first-time model download)
3. Sufficient disk space (~600MB for both models)

### Slow performance

**CPU mode is slow.** For production use:
1. Set `OBJECT_REMOVER_DEVICE=cuda` (requires NVIDIA GPU)
2. Install CUDA-enabled PyTorch
3. Reduce `ldmSteps` to 20-25

### Out of memory

**Reduce image size or use HD strategies:**
1. Use `hdStrategy="Resize"` with `hdStrategyResizeLimit=1024`
2. Or use `hdStrategy="Crop"` to process only the masked region
3. Reduce `ldmSteps` to 15-20

---

## Example Workflow

### Python Client

```python
import requests
import base64

# 1. Read image
with open('photo.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

# 2. Generate mask using SAM
files = {'image': open('photo.jpg', 'rb')}
data = {'points': '[{"x":213,"y":232}]'}
headers = {'X-API-Key': 'your-key-here'}

response = requests.post(
    'http://localhost:8000/api/object-remover/sam',
    files=files,
    data=data,
    headers=headers
)
mask_data = response.json()['mask']

# 3. Remove object
body = {
    'image': image_data,
    'mask': mask_data,
    'ldmSteps': 30,
    'maskExpand': 15
}

response = requests.post(
    'http://localhost:8000/api/object-remover/inpaint',
    json=body,
    headers={'X-API-Key': 'your-key-here', 'Content-Type': 'application/json'}
)

result_url = response.json()['result_url']
print(f'Result: {result_url}')
```

### JavaScript Client

```javascript
// 1. Upload image and get mask
const formData = new FormData();
formData.append('image', imageFile);
formData.append('points', JSON.stringify([{x: 213, y: 232}]));

const maskResponse = await fetch('/api/object-remover/sam', {
  method: 'POST',
  headers: {'X-API-Key': apiKey},
  body: formData
});
const {mask} = await maskResponse.json();

// 2. Convert image to base64
const imageBase64 = await fileToBase64(imageFile);

// 3. Remove object
const inpaintResponse = await fetch('/api/object-remover/inpaint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey
  },
  body: JSON.stringify({
    image: imageBase64.split(',')[1],
    mask: mask,
    ldmSteps: 25,
    maskExpand: 10
  })
});

const {result_url} = await inpaintResponse.json();
console.log('Result:', result_url);
```

---

## License & Credits

- **LaMa**: [Resolution-robust Large Mask Inpainting with Fourier Convolutions](https://github.com/advimman/lama)
- **SAM**: [Segment Anything Model by Meta AI](https://github.com/facebookresearch/segment-anything)
- **IOPaint**: [Image Inpainting Tool](https://github.com/Sanster/IOPaint)

This implementation wraps IOPaint's model interfaces for seamless integration with the FastAPI backend.
