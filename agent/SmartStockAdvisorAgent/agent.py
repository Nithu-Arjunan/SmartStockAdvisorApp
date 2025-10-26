import os
import warnings
import logging
import vertexai
from google import adk
from google.adk.agents import Agent
from google.adk import Runner
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search
from google.adk.agents.callback_context import CallbackContext
from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from .tools import get_youtubesummary,store_pdf,store_summary
from .Sub_agents.Data_Analyst_Agent import data_analyst_agent
from .Sub_agents.Trend_Analysis_Agent import trend_analyst_agent
from .prompt import FINAL_ANALYSIS_PROMPT
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID= os.getenv("AGENT_ENGINE_ID")
app_name ="Smart Stock Advisor"
user_id="user"


# --- Create a single global memory service instance ---
memory_service = VertexAiMemoryBankService(
    project="smart-stock-advisor",
    location=LOCATION,
    agent_engine_id=AGENT_ENGINE_ID
)

async def auto_save_to_memory_callback(callback_context):

    """Automatically save completed sessions to memory bank using default session user_id"""
     
    try:
        
        print("Entering auto_save_to_memory_callback")
        session_id = None

        # Extract session information from invocation context
        if hasattr(callback_context, "_invocation_context"):
            inv_ctx = callback_context._invocation_context

            # Extract session ID
            if hasattr(inv_ctx, "session") and hasattr(inv_ctx.session, "id"):
                session_id = inv_ctx.session.id

        # Get the session from the invocation context
        session = callback_context._invocation_context.session

        if not session_id:
            return
        print(f"Session ID: {session_id}")

        # Initialize memory service
        agent_engine_id = os.getenv("AGENT_ENGINE_ID")
        if not agent_engine_id:
            return

        # Check if session has meaningful content
        has_content = False
        content_count = 0

        if hasattr(session, "events") and session.events:
            content_count = len(session.events)
            has_content = content_count >= 2  # At least user message + agent response
        elif hasattr(session, "contents") and session.contents:
            content_count = len(session.contents)
            has_content = content_count >= 2

        if not has_content:
            return
        print("waiting")
        
        await memory_service.add_session_to_memory(session)
        print(f"Session auto-saved to memory bank")

    except Exception as e:
        print(f"Error auto-saving to memory: {e}")


async def search_memory(query: str) -> str:
    """
    Search Vertex AI memory bank for relevant information about the user's conversation.
    
    """
    print("Entering search_memory function")
    app_name ="SmartStockAdvisor"
    user_id ="user" 
    print(
        f"🔍 SEARCHING MEMORY BANK for app_name='{app_name}', user_id='{user_id}', query='{query}'..."
    )

    # memory_bank_service = VertexAiMemoryBankService(
    #     project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    #     location=os.getenv("GOOGLE_CLOUD_LOCATION"),
    #     agent_engine_id=os.getenv("AGENT_ENGINE_ID"),
    # )
    try:
        search_results = await memory_service.search_memory(
            app_name=app_name,
            user_id=user_id,
            query=query,
        )
        print(f"✅ SearchMemoryResponse: ")
        print(search_results)
        return search_results
    except Exception as e:
        print(f"❌ Error searching memory: {e}")
        return []


root_agent = Agent(
    name="Stock_Advisor_agent",
    model="gemini-2.5-flash",
    description=(
        "Agent to orchestrate all the agents and provide a detailed summary for the user query."
    ),
    instruction=FINAL_ANALYSIS_PROMPT,
    output_key="Final_analysis_output",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[
            AgentTool(agent=data_analyst_agent),
            AgentTool(agent=trend_analyst_agent),
            get_youtubesummary,
            store_pdf,
            search_memory,
            store_summary,
            google_search,
    ],
    after_agent_callback=auto_save_to_memory_callback,
    
)


