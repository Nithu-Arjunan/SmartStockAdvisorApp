import os
import uvicorn
import uuid 
import logging
import asyncio
import random

from fastapi import FastAPI,HTTPException,Request, Form
from fastapi.responses import FileResponse, JSONResponse,HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from agent.SmartStockAdvisorAgent.agent import root_agent
from agent.SmartStockAdvisorAgent.agent import auto_save_to_memory_callback
from agent.SmartStockAdvisorAgent.tools import store_pdf
#from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

# --- ADK Specific Imports ---
from google.adk.cli.fast_api import get_fast_api_app
from google.adk import Runner
from google.adk.sessions import VertexAiSessionService
from google.adk.memory import VertexAiMemoryBankService
from google.adk.artifacts import GcsArtifactService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.agents.run_config import RunConfig,StreamingMode
import vertexai
from google.cloud import aiplatform,storage
from google.api_core.exceptions import ResourceExhausted
from google.genai import types

from fastapi import Body
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
import google.auth

# --- New Imports for Retry Logic ---
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    retry_if_exception
)

# --- Retry Configuration ---
MAX_RETRIES = 3        # Max attempts before giving up
MAX_WAIT_SECONDS = 120     # Max time between retries

# To remove fileexists error
CACHE_DIR = os.path.expanduser("~/.cache/nsehistory-stock")
os.makedirs(CACHE_DIR, exist_ok=True)

# =============================================================================
# CONFIGURATION & RESOURCE INSTANTIATION
# =============================================================================

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_WEB_INTERFACE = True
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
app_name ="SmartStockAdvisor"
user_id="user"


# credentials, project = google.auth.default()
# aiplatform.init(project="smart-stock-advisor", location=LOCATION, credentials=credentials)
#vertexai.init(project="smart-stock-advisor", location="us-central1")
# artifact_service = GcsArtifactService(
#     project="smart-stock-advisor",
#     bucket_name=os.getenv("STORAGE_BUCKET", "smart-stock-report"),
# )

artifact_service = InMemoryArtifactService()

aiplatform.init(
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.environ["GOOGLE_CLOUD_LOCATION"]
)

session_service = VertexAiSessionService(
    project="smart-stock-advisor",
    location=LOCATION,
    agent_engine_id=AGENT_ENGINE_ID
)

# --- Create a single global memory service instance ---
memory_service = VertexAiMemoryBankService(
    project="smart-stock-advisor",
    location=LOCATION,
    agent_engine_id=AGENT_ENGINE_ID
)

runner=Runner(
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    app_name=app_name
)

run_config = RunConfig(
    #streaming_mode=StreamingMode.SSE,
    save_input_blobs_as_artifacts=True,
    max_llm_calls=10
)

# =============================================================================
# FASTAPI APPLICATION CREATION
# =============================================================================
FRONTEND_ORIGIN = "https://8000-cs-250789816200-default.cs-europe-west4-pear.cloudshell.dev"

ALLOWED_ORIGINS = [
    "http://localhost", 
    "http://localhost:8080", 
    FRONTEND_ORIGIN
]

app = FastAPI(title="SmartStockAdvisor")


app.mount("/static", StaticFiles(directory="static"), name="static")
#app.add_middleware(SessionMiddleware, secret_key="supersecret")
templates = Jinja2Templates(directory="templates")

# =============================================================================
# SETTING UP CORS
# =============================================================================

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:8080", FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

# =============================================================================
# CUSTOM ROUTES
# =============================================================================


@app.get("/api/data")
def get_data():
    return {"data": "Your actual stock data"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring & Cloud Run probes"""
    return {"status": "ok", "service": "Smart Stock Advisor"}


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/download/{filename}")
async def download_report(filename: str):
    bucket_name = os.getenv("STORAGE_BUCKET", "smart-stock-report")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    local_path = f"/tmp/{filename}"
    blob.download_to_filename(local_path)
    return FileResponse(local_path, filename=filename)

#============================================================================
# Helper function for retry
#============================================================================

def is_rate_limit_error(exception: Exception) -> bool:
    """
    Checks if the exception is a 429 Resource Exhausted error, 
    even if it's wrapped in a different exception type.
    """
    # 1. Check for the official type (best practice)
    if isinstance(exception, ResourceExhausted):
        return True
        
    # 2. Check for attributes common in gRPC/HTTP status exceptions
    # The ADK exception often includes 'code', 'status_code', or the message
    if hasattr(exception, 'code') and exception.code == 429:
        return True
    if hasattr(exception, 'status_code') and exception.status_code == 429:
        return True
        
    # 3. Last resort: Check the string representation of the error (reliable for your specific error)
    error_message = str(exception).lower()
    if '429 resource_exhausted' in error_message or 'quota exceeded' in error_message:
        return True
        
    return False

@retry(
    # Exponential backoff with jitter (1s, 2s, 4s, etc., up to 60s)
    wait=wait_random_exponential(min=1, max=MAX_WAIT_SECONDS),
    # Stop after 5 attempts total
    stop=stop_after_attempt(MAX_RETRIES),
    # Only retry if the 429 error (ResourceExhausted) is raised
    retry=retry_if_exception(is_rate_limit_error),  
    before_sleep=lambda retry_state: print(
        f"Rate limit hit (429). Retrying in ~{retry_state.next_wait_time:.1f}s (Attempt {retry_state.attempt_number}/{MAX_RETRIES})."
    )
)
async def _run_agent_with_retry(runner, session_id: str, content: types.Content) -> str:
    """
    Executes the ADK agent run and aggregates the response,
    designed to be retried automatically on a 429 ResourceExhausted error.
    """
    final_response_text = ""
    
    async for event in runner.run_async(user_id="user", session_id=session_id, new_message=content,run_config=run_config):
        # Debug log
        print("I am here in DEBUG (Retriable)")
        print("DEBUG EVENT:", event)

        if hasattr(event, "Final_analysis_output") and event.Final_analysis_output:
            print(f"Agent Success: Final output found in 'Final_analysis_output'.")
            return event.Final_analysis_output.strip()
        # 1️⃣ Check normal text content
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    #final_response_text += part.text.strip() + "\n"
                    return part.text
    #Generate memories
    # await memory_service.generate_memories(
    #     reasoning_engine_name=AGENT_ENGINE_ID,
    #     direct_memories_source={
    #         "memories": [
    #             {"fact": f"User said: {content}"},
    #             {"fact": f"Agent responded: {Final_analysis_output}"}
    #         ]
    #     },
    #     scope={"user_id": user_id}
    # )

    # Add to memory bank
    await self.memory_service.add_session_to_memory(session)
    print("✅ Session saved to memory bank!")

    # Return the aggregated response text
    return final_response_text.strip()
      

#=================End of function=========================================================

@app.post("/chat/stream")
async def chat_stream(request: Request):
    data = await request.json()
    user_input = data.get("user_input")
    user_id = data.get("user_id", "user")
    session_id = data.get("session_id")
    
    USER_ID="user"
    if not user_input:
        return {"error": "User input not provided"}

    print(f"User: {user_id}, Question: {user_input}")

     # --- Agent Interaction ---
    try:

        if not session_id:
            print("Creating a new ADK session...")
            session = await session_service.create_session(app_name="SmartStockAdvisor", user_id="user")
            session_id = session.id

        else:
            # Reuse the existing session
            session_id = session_id
            print(f"Reusing existing session ID: {session_id}")

        content = types.Content(role='user', parts=[types.Part(text=user_input)])

        # --- Agent Interaction with Retry Logic ---
        
        # 1. CALL THE RETRIABLE FUNCTION
        final_response_text = await _run_agent_with_retry(
            runner=runner, 
            session_id=session_id, 
            content=content
        )
        
        # 2. Return success response
        return {"response": final_response_text or "No response", "session_id": session_id}

    except Exception as e:
        # Check if the final failed exception (after max retries) is a 429
        if is_rate_limit_error(e):
            print(f"CRITICAL Error: All {MAX_RETRIES} retries failed due to quota exhaustion (429).")
            # Return a 429 HTTP status to the frontend
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please try again later. The service is currently busy."
            )
        else:
            # Handle all other non-429 exceptions
            print(f"Error interacting with agent: {e}")
            raise HTTPException(status_code=500, detail=f"Agent interaction failed: {str(e)}")
    

# =============================================================================
# APPLICATION STARTUP CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
