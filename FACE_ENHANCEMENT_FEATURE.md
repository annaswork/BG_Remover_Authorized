# Face Enhancement Feature

## Overview
This document describes the face enhancement feature added to the face swap functionality.

## Features Added

### 1. Enhancement Flag in Face Swap API
The `/api/face_detect/swap` endpoint now accepts an optional `enhance` parameter:

**Endpoint:** `POST /api/face_detect/swap`

**Parameters:**
- `source` (file, required): Source image with exactly one face
- `target` (file, required): Target image with one or more faces
- `enhance` (boolean, optional, default=False): Apply GFPGAN enhancement to the swapped result

**Response:**
```json
{
  "message": "Faces swapped successfully",
  "image_url": "http://example.com/results/output.webp",
  "filename": "output.webp",
  "time_taken": "2.45",
  "enhanced": true
}
```

### 2. Standalone Enhancement API
A new endpoint for enhancing any image using GFPGAN:

**Endpoint:** `POST /api/face_detect/enhance`

**Parameters:**
- `file` (file, required): Image file to enhance

**Response:**
```json
{
  "message": "Image enhanced successfully",
  "image_url": "http://example.com/results/enhanced.webp",
  "filename": "enhanced.webp",
  "time_taken": "1.23"
}
```

### 3. Web UI Updates

#### Enhancement Toggle
- Added a checkbox in the Face Swap page to enable/disable enhancement during face swap
- Label: "Apply GFPGAN Enhancement (improves face quality but takes longer)"
- Located above the "Swap Faces" button

#### Enhance Button
- When face swap is performed WITHOUT enhancement, an "Enhance Image" button appears next to the download button
- Clicking this button calls the `/api/face_detect/enhance` endpoint with the swapped image
- After enhancement, the button is hidden and the enhanced image replaces the original
- The button is also hidden if enhancement was already applied during the swap

## Usage Examples

### Example 1: Face Swap with Enhancement
```python
import requests

url = "http://your-server/api/face_detect/swap"
headers = {"X-API-Key": "your-api-key"}
files = {
    "source": open("source.jpg", "rb"),
    "target": open("target.jpg", "rb")
}
data = {"enhance": "true"}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Example 2: Face Swap without Enhancement
```python
import requests

url = "http://your-server/api/face_detect/swap"
headers = {"X-API-Key": "your-api-key"}
files = {
    "source": open("source.jpg", "rb"),
    "target": open("target.jpg", "rb")
}
data = {"enhance": "false"}  # or omit this parameter

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Example 3: Standalone Image Enhancement
```python
import requests

url = "http://your-server/api/face_detect/enhance"
headers = {"X-API-Key": "your-api-key"}
files = {"file": open("image.jpg", "rb")}

response = requests.post(url, headers=headers, files=files)
print(response.json())
```

## Technical Details

### Backend Changes

1. **controller/face_app_controller.py**
   - Modified `face_swap_func()` to accept an `enhance` parameter
   - Added conditional enhancement logic based on the flag
   - Added new `enhance_image_func()` for standalone enhancement
   - Added new `enhance_image()` async wrapper

2. **router/face_app_router.py**
   - Updated `/swap` endpoint to accept `enhance` form parameter
   - Added new `/enhance` endpoint for standalone enhancement

### Frontend Changes

1. **templates/index.html**
   - Added enhancement toggle checkbox in the face swap section
   - Added "Enhance Image" button that appears conditionally
   - Updated `swapFaces()` function to send the enhance parameter
   - Added new `enhanceSwappedImage()` function to handle post-swap enhancement
   - Updated `resetSwap()` to reset enhancement-related UI elements

## Performance Considerations

- Enhancement using GFPGAN adds processing time (typically 1-3 seconds depending on image size)
- Users can choose to skip enhancement during swap for faster results
- Post-swap enhancement allows users to preview the unenhanced result first

## Notes

- The GFPGAN model must be initialized on the server for enhancement to work
- If the enhancement model is not available, the API will return a 500 error
- Enhancement is optional and the face swap will work without it
