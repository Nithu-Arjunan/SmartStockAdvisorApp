import datetime
import warnings
import logging
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.genai import types
from .prompt import DATA_ANALYSIS_PROMPT

data_analyst_agent = Agent(
    name="data_analyst_agent",
    model="gemini-2.5-flash",
    description=(
        "Agent to collect all the information related to the stocks."
    ),
    instruction=DATA_ANALYSIS_PROMPT,
    output_key="Analysis_report",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[google_search],
)