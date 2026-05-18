# Object Remover - Quick Start Guide

Get the Object Remover feature up and running in 5 minutes.

---

## Prerequisites

- Python 3.8+
- MongoDB running on localhost:27017
- ~600MB free disk space (for model downloads)
- Internet connection (for first-time model download)

---

## Installation

### Step 1: Install Dependencies

```bash
pip install iopaint>=1.3.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

The `.env` file has already been updated with:

```env
LAMA_ENABLE=true
LAMA_MODEL_TYPE=lama
SAM_ENABLE=true
SAM_MODEL_TYPE=sam
OBJECT_REMOVER_DEVICE=cpu
```

**For GPU acceleration** (requires NVIDIA GPU + CUDA):
```env
OBJECT_REMOVER_DEVICE=cuda
```

### Step 3: Start the Server

```bash
python run.py
```

**First startup will take 2-3 minutes** as models download automatically:
- LaMa model: ~200MB
- SAM model: ~350MB

You'll see:
```
[Models Init] Loading LaMa model (lama) on cpu...
[Models Init] LaMa model loaded successfully
[Models Init] Loading SAM model (sam) on cpu...
[Models Init] SAM model loaded successfully
```

---

## Quick Test

### Option 1: Web UI (Recommended)

1. Open browser: `http://localhost:8000/`
2. Click **"Object Remover"** in the sidebar
3. Check model status (should show "✓ Loaded" for both)
4. Enter your API key
5. Upload a test image
6. Click on an object you want to remove
7. Click **"Generate Mask"**
8. Review the mask and click **"Remove Object"**
9. Download the result!

### Option 2: API Test (cURL)

#### 1. Generate API Key (if you don't have one)

```bash
curl -X POST http://localhost:8000/api/auth/generate-key \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"app_name": "test"}'
```

#### 2. Check Model Status

```bash
curl http://localhost:8000/api/object-remover/health
```

Expected response:
```json
{
  "status": "ok",
  "lama_loaded": true,
  "sam_loaded": true
}
```

#### 3. Generate Mask (SAM)

```bash
curl -X POST http://localhost:8000/api/object-remover/sam \
  -H "X-API-Key: your-api-key" \
  -F "image=@test_image.jpg" \
  -F 'points=[{"x":200,"y":300}]'
```

#### 4. Remove Object (LaMa)

```bash
curl -X POST http://localhost:8000/api/object-remover/inpaint-file \
  -H "X-API-Key: your-api-key" \
  -F "image=@test_image.jpg" \
  -F "mask=@mask.png" \
  -F "ldmSteps=25" \
  -F "maskExpand=10"
```

---

## Common Issues

### Issue: Models Not Loading

**Check logs for:**
```
[Models Init] Warning: Could not load LaMa model: ...
```

**Solutions:**
1. Verify internet connection
2. Check disk space (~600MB needed)
3. Try restarting the server
4. Check firewall isn't blocking model downloads

### Issue: "Module 'iopaint' not found"

**Solution:**
```bash
pip install iopaint>=1.3.0
```

### Issue: Slow Performance

**For CPU mode**, expect:
- SAM: 3-5 seconds
- LaMa: 10-15 seconds

**To speed up**, use GPU:
```env
OBJECT_REMOVER_DEVICE=cuda
```

Then install CUDA-enabled PyTorch:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## Usage Tips

### For Best Quality
- Use **ldmSteps=40-50** (slower but better)
- Use **maskExpand=15-20** (cleaner edges)
- Add multiple click points for complex objects

### For Speed
- Use **ldmSteps=15-20** (faster but lower quality)
- Use **SAM_MODEL_TYPE=sam2** (faster segmentation)
- Use **hdStrategy="Crop"** for large images

### For Large Images
- Use **hdStrategy="Resize"** with **hdStrategyResizeLimit=1024**
- Or use **hdStrategy="Crop"** to process only masked region

---

## Next Steps

1. **Read full documentation**: [OBJECT_REMOVER_FEATURE.md](./OBJECT_REMOVER_FEATURE.md)
2. **Review integration details**: [INTEGRATION_SUMMARY.md](./INTEGRATION_SUMMARY.md)
3. **Check main README**: [README.md](./README.md)
4. **Test with your own images**
5. **Adjust quality settings** based on your needs

---

## API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/object-remover/health` | GET | No | Check model status |
| `/api/object-remover/sam` | POST | Yes | Generate mask from clicks |
| `/api/object-remover/inpaint` | POST | Yes | Remove object (JSON) |
| `/api/object-remover/inpaint-file` | POST | Yes | Remove object (files) |
| `/api/object-remover/clear-results` | DELETE | Yes | Clear saved results |

---

## Support

- **Documentation**: See [OBJECT_REMOVER_FEATURE.md](./OBJECT_REMOVER_FEATURE.md)
- **Troubleshooting**: Check server logs and model status
- **Performance**: Adjust settings based on your hardware

---

**You're all set!** 🎉

The Object Remover is now integrated and ready to use. Start by testing with the web UI, then explore the API for programmatic access.
