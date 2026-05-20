from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from controller.bp_report_controller import BPReportRequest, generate_bp_report
from controller.auth_controller import require_api_key

router = APIRouter(prefix="/api/bp-report", tags=["bp-report"])


@router.get("/", response_model=dict)
async def bp_report_health():
    """Health-check endpoint for the BP Report service."""
    return {"flag": True, "message": "Server Running", "appname": "BP Report"}


@router.post("/health-report", response_class=HTMLResponse)
async def health_report(
    request: Request,
    body: BPReportRequest,
    _auth: dict = Depends(require_api_key),
):
    """
    Generate an AI-powered blood pressure health report.

    Accepts patient vitals (systolic, diastolic, heart_rate, age, weight,
    height, gender) and returns a rendered HTML report with GPT-generated
    clinical recommendations.

    Requires a valid API key in the **X-API-Key** header.
    """
    return await generate_bp_report(request, body)
