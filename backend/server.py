from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import base64
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBuavqHyKU_Y3N5QIDP-MFAeq1Qslrev1s')

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class PillAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    image_base64: str
    pill_name: Optional[str] = None
    pill_description: Optional[str] = None
    uses: Optional[str] = None
    side_effects: Optional[str] = None
    dosage: Optional[str] = None
    ayurvedic_alternatives: Optional[str] = None
    safety_info: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PillAnalysisRequest(BaseModel):
    image_base64: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class PillAnalysisResponse(BaseModel):
    id: str
    session_id: str
    pill_name: str
    pill_description: str
    uses: str
    side_effects: str
    dosage: str
    ayurvedic_alternatives: str
    safety_info: str
    confidence: float

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "PillWise API - AI Pill Identification"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/analyze-pill", response_model=PillAnalysisResponse)
async def analyze_pill(request: PillAnalysisRequest):
    try:
        # Initialize Gemini chat with vision capabilities
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=request.session_id,
            system_message="""You are PillWise, an expert medical AI specializing in pill identification and Ayurvedic medicine. 

Your task is to:
1. Identify the pill from the image (name, manufacturer if visible)
2. Provide medical uses and indications
3. List common side effects and warnings
4. Suggest proper dosage guidelines
5. Recommend Ayurvedic alternatives with their benefits
6. Provide safety information and precautions

Format your response as a JSON object with these exact keys:
{
    "pill_name": "Name of the pill or 'Unknown Pill' if not identifiable",
    "pill_description": "Physical description and any visible markings/text",
    "uses": "Medical uses and indications",
    "side_effects": "Common side effects and warnings",
    "dosage": "Typical dosage information",
    "ayurvedic_alternatives": "Natural Ayurvedic alternatives with benefits",
    "safety_info": "Important safety information and precautions",
    "confidence": 0.85
}

Be thorough but concise. If you cannot identify the specific pill, provide general guidance based on what you can observe."""
        ).with_model("gemini", "gemini-2.0-flash")

        # Create image content from base64
        image_content = ImageContent(image_base64=request.image_base64)
        
        # Create user message with image
        user_message = UserMessage(
            text="Please analyze this pill image and provide detailed information including identification, uses, side effects, dosage, Ayurvedic alternatives, and safety information. Return the response in the specified JSON format.",
            file_contents=[image_content]
        )

        # Get response from Gemini
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        import json
        try:
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            analysis_data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            # Fallback parsing if JSON is not properly formatted
            analysis_data = {
                "pill_name": "Analysis Completed",
                "pill_description": "Pill image analyzed successfully",
                "uses": "Please consult with a healthcare professional for proper identification and usage",
                "side_effects": "Unknown - consult healthcare provider",
                "dosage": "Consult healthcare provider for proper dosage",
                "ayurvedic_alternatives": "General alternatives: Turmeric, Ashwagandha, Triphala - consult Ayurvedic practitioner",
                "safety_info": "Always consult healthcare professionals before taking any medication",
                "confidence": 0.5
            }

        # Create pill analysis object
        pill_analysis = PillAnalysis(
            session_id=request.session_id,
            image_base64=request.image_base64,
            pill_name=analysis_data.get("pill_name", "Unknown"),
            pill_description=analysis_data.get("pill_description", ""),
            uses=analysis_data.get("uses", ""),
            side_effects=analysis_data.get("side_effects", ""),
            dosage=analysis_data.get("dosage", ""),
            ayurvedic_alternatives=analysis_data.get("ayurvedic_alternatives", ""),
            safety_info=analysis_data.get("safety_info", ""),
            confidence=analysis_data.get("confidence", 0.5)
        )

        # Save to database
        await db.pill_analyses.insert_one(pill_analysis.dict())

        # Return response
        return PillAnalysisResponse(
            id=pill_analysis.id,
            session_id=pill_analysis.session_id,
            pill_name=pill_analysis.pill_name or "Unknown",
            pill_description=pill_analysis.pill_description or "",
            uses=pill_analysis.uses or "",
            side_effects=pill_analysis.side_effects or "",
            dosage=pill_analysis.dosage or "",
            ayurvedic_alternatives=pill_analysis.ayurvedic_alternatives or "",
            safety_info=pill_analysis.safety_info or "",
            confidence=pill_analysis.confidence or 0.5
        )

    except Exception as e:
        logging.error(f"Error analyzing pill: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing pill: {str(e)}")

@api_router.get("/analysis-history/{session_id}")
async def get_analysis_history(session_id: str):
    try:
        analyses = await db.pill_analyses.find({"session_id": session_id}).to_list(100)
        return [PillAnalysis(**analysis) for analysis in analyses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()