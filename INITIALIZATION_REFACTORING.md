# Initialization Refactoring

## Overview
This document describes the refactoring of the application initialization logic to eliminate code duplication and follow the Single Responsibility Principle (SRP).

## Changes Made

### 1. **Removed Duplicate Lifespan Function**

**Before:**
- `lifespan` function was defined in both `database/index.py` and `app.py`
- This caused code duplication and maintenance issues

**After:**
- `lifespan` function is defined only in `database/index.py`
- `app.py` imports it from `database/index.py`

**Files Modified:**
- `app.py`: Removed duplicate lifespan definition, now imports from `database/index.py`

### 2. **Centralized Model Initialization**

**Before:**
- PlantProfiler initialization was scattered or missing
- No clear place for global model instances

**After:**
- All model instances (including PlantProfiler) are initialized in `inits/models_init.py`
- PlantProfiler is conditionally initialized based on `OPENAI_API_KEY` environment variable

**Files Modified:**
- `inits/models_init.py`: Added PlantProfiler initialization

### 3. **Enhanced Lifespan Management**

**Before:**
- `database/index.py` only handled MongoDB connection
- No startup/shutdown for PlantProfiler

**After:**
- `database/index.py` now handles:
  - MongoDB connection (startup/shutdown)
  - PlantProfiler startup/shutdown (if available)
  - Proper logging for all lifecycle events

**Files Modified:**
- `database/index.py`: Enhanced with PlantProfiler lifecycle management

### 4. **Model Download Logic**

**Note:** Model downloading is already properly handled in `models/load_models.py`:
- Models are downloaded automatically on first import if they don't exist
- Each model checks for existence before downloading
- No need for separate `download_models_if_needed()` function in lifespan

## Architecture

### Initialization Flow

```
1. Application Start
   ↓
2. Import inits/models_init.py
   ├─ Load face_model (from models/load_models.py)
   ├─ Load swapper (from models/load_models.py)
   ├─ Load gfpgan_model (from models/load_models.py)
   └─ Initialize plant_profiler (if OPENAI_API_KEY exists)
   ↓
3. Import database/index.py
   └─ Define lifespan function
   ↓
4. Import app.py
   ├─ Import lifespan from database/index.py
   └─ Attach lifespan to app
   ↓
5. Lifespan Startup (when app starts)
   ├─ Connect to MongoDB
   └─ Start PlantProfiler (if available)
   ↓
6. Application Running
   ↓
7. Lifespan Shutdown (when app stops)
   ├─ Shutdown PlantProfiler (if available)
   └─ Close MongoDB connection
```

### File Responsibilities

#### `inits/models_init.py`
- **Purpose:** Initialize all ML models and AI services as global variables
- **Exports:**
  - `face_model`: InsightFace model for face detection
  - `swapper`: Face swapper model
  - `gfpgan_model`: GFPGAN enhancement model (optional)
  - `plant_profiler`: PlantProfiler instance (optional, requires OPENAI_API_KEY)

#### `database/index.py`
- **Purpose:** Define application lifespan management
- **Exports:**
  - `lifespan`: AsyncContextManager for app startup/shutdown
- **Responsibilities:**
  - MongoDB connection management
  - PlantProfiler lifecycle management
  - Logging lifecycle events

#### `app.py`
- **Purpose:** Main application entry point
- **Responsibilities:**
  - Import and configure FastAPI app
  - Attach lifespan manager
  - Register middleware
  - Include routers

#### `models/load_models.py`
- **Purpose:** Load ML models with automatic downloading
- **Behavior:**
  - Checks if model files exist
  - Downloads missing models automatically
  - Exports model instances as module-level variables

## Benefits

### 1. **No Code Duplication**
- Single source of truth for each initialization concern
- Easier to maintain and update

### 2. **Clear Separation of Concerns**
- Models → `inits/models_init.py`
- Database & Lifecycle → `database/index.py`
- App Configuration → `app.py`
- Model Loading → `models/load_models.py`

### 3. **Conditional Initialization**
- PlantProfiler only initializes if `OPENAI_API_KEY` is set
- Graceful degradation if optional services are unavailable

### 4. **Proper Lifecycle Management**
- Startup and shutdown are properly handled
- Resources are cleaned up on application exit
- Clear logging for debugging

### 5. **Automatic Model Downloads**
- Models download automatically on first use
- No need for manual download step
- Handled transparently by `models/load_models.py`

## Environment Variables

### Required
- `MONGODB_URI`: MongoDB connection string

### Optional
- `OPENAI_API_KEY`: Required for PlantProfiler functionality
  - If not set: PlantProfiler will not be initialized
  - If set: PlantProfiler will be available for plant profile generation

## Usage

### Accessing Models in Controllers

```python
# Import models from inits/models_init.py
from inits.models_init import face_model, swapper, gfpgan_model, plant_profiler

# Use in your controller
async def my_controller():
    if plant_profiler:
        profile = await plant_profiler.get_profile(
            scientific_name="Rosa canina",
            family="Rosaceae",
            genus="Rosa"
        )
    # ... rest of your logic
```

### Adding New Models

To add a new model to the initialization:

1. Add loading logic to `models/load_models.py`
2. Import and expose in `inits/models_init.py`
3. If it needs lifecycle management, add to `database/index.py` lifespan function

## Testing

To verify the initialization:

1. **Without OPENAI_API_KEY:**
   ```bash
   # Remove or comment out OPENAI_API_KEY in .env
   python run.py
   ```
   Expected output:
   ```
   [Models Init] Warning: OPENAI_API_KEY not set in .env file
   [Models Init] Plant profile generation will not be available
   [Lifespan] Starting up...
   [Lifespan] Startup complete
   ```

2. **With OPENAI_API_KEY:**
   ```bash
   # Set OPENAI_API_KEY in .env
   python run.py
   ```
   Expected output:
   ```
   [Models Init] PlantProfiler initialized successfully
   [Lifespan] Starting up...
   [PlantProfiler] Ready — X cached profiles loaded.
   [Lifespan] PlantProfiler started successfully
   [Lifespan] Startup complete
   ```

## Migration Notes

If you have existing code that:
- Defines `lifespan` in `app.py` → Remove it, import from `database/index.py`
- Calls `download_models_if_needed()` → Remove it, models auto-download
- Initializes PlantProfiler elsewhere → Move to `inits/models_init.py`

## Future Improvements

1. Consider adding health check endpoints for each service
2. Add metrics for model loading times
3. Implement graceful degradation for failed model loads
4. Add configuration for model download retry logic
