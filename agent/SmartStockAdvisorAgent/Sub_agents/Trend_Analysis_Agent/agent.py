import os
import io
import math
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import base64
import logging
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from jugaad_data.nse import bhavcopy_save, bhavcopy_fo_save
from jugaad_data.nse import stock_df
from google.adk.tools import ToolContext
from google import genai
from google.genai import types
from google.genai.types import Part
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from .prompt import return_instructions
import google.genai.types as types

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(   
    level=logging.INFO,             
    format="%(asctime)s - %(levelname)s - %(message)s"
)

artifact_service = InMemoryArtifactService()

def load_stock_data(stock_name: str,tool_context: ToolContext) -> dict:
    """Function to download five years past data from NSE and plot graph.

    Args:
        stock_name (str): The name of the stock for which the data has to be retrieved.

    Returns:
        dict: Returns a dictionary which includes the generated plot.
    """
  
    today = datetime.now()
    year= today.year
    month = today.month
    day = today.day
    five_yrs_ago = datetime.now() - relativedelta(years=5)
   

    # Download stock data to pandas dataframe
    
    try:
        logging.info("Starting to plot monthly closing trend graph.")
        df = stock_df(
            symbol=stock_name,
            from_date=date(five_yrs_ago.year, five_yrs_ago.month, five_yrs_ago.day),
            to_date=date(today.year, today.month, today.day),
            series="EQ"
        )
    except ValueError as e:  
       
        return {"error": f"Failed to fetch stock data for {stock_name}: {e}"}

    if df.empty:
        return {"error": f"No data returned for {stock_name}"}

    df = df.sort_values(by='DATE', ascending=True)
    
    try:
        # Plot graphs 
        print("Plotting graphs here")
        df["DATE"] = pd.to_datetime(df["DATE"])

        df_monthly = df.resample("ME", on="DATE")["CLOSE"].mean()
        plt.figure(figsize=(10,5))
        plt.plot(df_monthly.index, df_monthly.values, marker='o')
        plt.title(" Monthly Closing Trend –")
        plt.xlabel("Month")
        plt.ylabel("Closing Price")
        plt.grid(True)
        plt.show()
        logging.info("Graph plotted successfully.")
    except Exception as e:
        logging.error("Error while plotting graph: %s", e, exc_info=True)
  
     # --- Save to buffer ---
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    image_bytes = base64.b64encode(buf.getvalue()).decode('utf-8')

    image_artifact = types.Part(
    inline_data=types.Blob(
        mime_type="image/png",
        data=image_bytes
        )
    )

    return (image_artifact.inline_data)


trend_analyst_agent = Agent(

    name="trend_analyst_agent",
    model="gemini-2.5-flash",
    #code_executor=BuiltInCodeExecutor(),
    description=(
        "Agent to download five year data from NSE,plot a graph and provide an analysis."
    ),
    output_key="trend_analysis_report",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[load_stock_data],
    instruction=return_instructions(),
   
)

