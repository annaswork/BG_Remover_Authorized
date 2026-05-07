from fastapi import APIRouter, UploadFile, File, Depends, Request, Query
from controller.auth_controller import require_api_key
from controller.plant_id_controller import predict_plant, search_plant, get_more_info

router = APIRouter(prefix="/api/plant-id", tags=["plant-id"])

@router.post("/predict", response_model=dict)
async def predict(
    file: UploadFile = File(..., description="Image of the plant to identify"),
    top_k: int = Query(1, ge=1, le=20, description="Number of top results to return (only top 1 is returned)"),
    _auth: dict = Depends(require_api_key)
):
    """
    Identify a plant from an uploaded image using local BioCLIP model and FAISS index.
    Returns basic information (scientific name, common name) only.
    Use /get-more-info endpoint to fetch full plant profile.
    
    Note: Currently only returns top 1 result regardless of top_k parameter.
    
    Returns:
        - message: Status message
        - results: Array with the top match including rank, similarity score, and basic metadata
        - top_match: The best match (first result)
    """
    return await predict_plant(file, 1)  # Always return top 1

@router.get("/get-more-info", response_model=dict)
async def get_plant_more_info(
    scientific_name: str = Query(..., description="Scientific name of the plant"),
    _auth: dict = Depends(require_api_key)
):
    """
    Get full plant profile information for a specific plant.
    Checks MongoDB cache first, calls LLM if not found.
    
    Query Parameters:
        - scientific_name: The scientific name of the plant (required)
    
    Returns:
        - message: Status message
        - data: Full plant profile with care instructions, taxonomy, etc.
        - source: "database" or "llm" indicating where data came from
    """
    return await get_more_info(scientific_name)

@router.get("/search", response_model=dict)
async def search(
    scientific_name: str = Query(None, description="Scientific name of the plant"),
    name: str = Query(None, description="Alternative to scientific_name"),
    family: str = Query("", description="Plant family (optional, improves LLM accuracy)"),
    genus: str = Query("", description="Plant genus (optional, improves LLM accuracy)"),
    validate: bool = Query(True, description="Enable botanical query validation"),
    _auth: dict = Depends(require_api_key)
):
    """
    Search for detailed plant information by scientific name.
    Generates a comprehensive botanical profile using OpenAI LLM.
    Requires a valid API key in the X-API-Key header.
    
    Query Parameters:
        - scientific_name or name: The scientific name of the plant (required)
        - family: Plant family for better LLM context (optional)
        - genus: Plant genus for better LLM context (optional)
        - validate: Enable botanical guard to reject non-plant queries (default: true)
    
    Returns:
        - message: Status message
        - data: Detailed plant profile with care instructions, taxonomy, etc.
        - is_botanical: Whether the query passed validation
        
    If validation fails (validate=true and query is not botanical):
        - error: Error message
        - suggestion: Suggested plant name correction
        - reason: Explanation of why validation failed
    """
    query_params = {
        "scientific_name": scientific_name,
        "name": name,
        "family": family,
        "genus": genus,
        "validate": str(validate).lower()
    }
    return await search_plant(query_params)
