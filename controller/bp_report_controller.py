import json
import re
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from utils.chatgptFunction import search_gpt

templates = Jinja2Templates(directory="templates")


def _extract_json(text: str) -> str:
    """
    Strip markdown code fences and extract the first JSON object from text.
    GPT sometimes wraps its response in ```json ... ``` or adds prose around it.
    """
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    # Extract the first {...} block in case there is surrounding prose
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


# ── Request schema ────────────────────────────────────────────────────────────

class BPReportRequest(BaseModel):
    systolic: int
    diastolic: int
    heart_rate: int
    patient_age: int
    patient_weight: str   # e.g. "70 kg"
    patient_height: str   # e.g. "175 cm"
    patient_gender: str   # e.g. "male" / "female"


# ── Controller logic ──────────────────────────────────────────────────────────

async def generate_bp_report(request: Request, body: BPReportRequest):
    """
    Build a GPT prompt from the patient vitals, parse the JSON response,
    and render it into report.html as an HTMLResponse.
    """
    prompt = f"""I am a {body.patient_age}-year-old {body.patient_gender}, \
weighing {body.patient_weight} and standing {body.patient_height} tall.
My blood pressure is {body.systolic}/{body.diastolic} mmHg, \
and my heart rate is {body.heart_rate} bpm.
Generate a report, the response should only contain the dictionary object, properly formatted.
There should be no data other than the "value" keeping the given key:
    {{
        "Interpretation": "value",
        "Caution": "value",
        "Medication": "value",
        "Nutrition": "value",
        "Physical_Activity": "value",
        "Mental_Health": "value",
        "Preventive_Care": "value",
        "Sleep_Hygiene": "value",
        "Avoid_Harmful_Behaviors": "value"
    }}"""

    system_prompt = "You are a helpful Physician who will help me with how to improve health outcomes."
    raw = search_gpt(prompt, system_prompt, json_mode=True)
    print("[bp_report] GPT raw response:", raw)

    if not raw:
        raise HTTPException(status_code=502, detail="GPT service returned an empty response.")

    try:
        report = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        print("[bp_report] JSON decode error. Raw GPT response was:", raw)
        raise HTTPException(status_code=502, detail="GPT response could not be parsed as JSON.")

    # Merge patient vitals into the template context
    report.update(
        Patient_Age=body.patient_age,
        Patient_Weight=body.patient_weight,
        Patient_Height=body.patient_height,
        Patient_Gender=body.patient_gender,
        systolic=body.systolic,
        diastolic=body.diastolic,
        heart_rate=body.heart_rate,
    )

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context=report,
        headers={"content-type": "text/html; charset=utf-8"},
    )
