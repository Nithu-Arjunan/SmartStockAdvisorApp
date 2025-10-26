import os
import asyncio
import json
import logging
import io
import base64
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT,TA_CENTER
from google.cloud import storage
from google import genai
from google.genai.types import Part
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from googleapiclient.discovery import build
from google.cloud import bigquery
from tenacity import retry, wait_random_exponential, stop_after_attempt

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
API_KEY = os.environ["YouTube_data_API"]
STORAGE_BUCKET = os.environ["STORAGE_BUCKET"]
staging_bucket = "gs://" + STORAGE_BUCKET
logger = logging.getLogger(__name__)

# Initialize BigQuery client
client = bigquery.Client(project="smart-stock-advisor")
TABLE_ID = "smart-stock-advisor.Summary.Results" 


#============================ FUNCTION DEFINITION========================================================

async def get_youtubesummary(stock_name: str) -> dict:
    
    """Async Tool to search for top 5 recent videos on YouTube and retrieve a combined summary.


    Args:
        stock_name (str): The name of the stock for which the summary has to be retrieved.

    Returns:
        dict: status and summary of the stock or error msg."""
    

    SEARCH_KEYWORD = stock_name
    MAX_RESULTS = 3

    GEMINI_PRO_MODEL_ID = "gemini-2.5-flash"
    SUMMARY_PROMPT = f"""
    You are a video analysis Agent.
    Summarize each videos and look for content realted to {SEARCH_KEYWORD}.
    Ignore the video if the video generation date is more than two years old from the current date.Do not include older videos for summary generation.
    Afer analyzing all the three videos provide a summary of only contents related to {SEARCH_KEYWORD}.Do NOT INCLUDE ANY VIDEOS REALTEDD TO UNBOXING.
    Strictly include only those videos related to stocks.
    Provide only the final summary as the output.The final summary should include contents of all the videoa analysed and summarized.
    """

    # --- Initialize GenAI Client ---
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    # --- Search YouTube ---
    def search_youtube_videos(keyword, api_key, max_results=3):
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part="snippet", q=keyword, type="video", maxResults=max_results, order="relevance"
        )
        response = request.execute()

        results = []
        for item in response["items"]:
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            results.append({"title": title, "url": url})
        return results

    # --- Async Summarization Function ---
    @retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(2))
    async def async_generate_summary(prompt, yt_link):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_PRO_MODEL_ID,
                contents=[
                    Part.from_uri(file_uri=yt_link, mime_type="video/webm"),
                    prompt
                ]
            )
            return response.candidates[0].content.parts[0].text
        except Exception as e:
            print(f"Error processing {yt_link}: {e}")
            return None

  
     # Search for videos
    top_videos = search_youtube_videos(SEARCH_KEYWORD, API_KEY, MAX_RESULTS)

    # Summarize videos concurrently
    summaries = await asyncio.gather(
        *[async_generate_summary(SUMMARY_PROMPT, vid["url"]) for vid in top_videos]
    )

    # Filter out None values
    valid_summaries = [s for s in summaries if s]

    if not valid_summaries:
        return {"error": "No valid summaries could be generated."}

    # Combine final summary
    combined_summary = "\n\n".join(valid_summaries)

    # Return as dictionary 
    return {
        "status": "success",
        "stock": stock_name,
        "summary": combined_summary
    }


#============================ FUNCTION DEFINITION========================================================
            

async def store_pdf(content: str , tool_context: ToolContext) -> dict:
    """
    Stores the given text content into a PDF file in the Cloud Storage bucket 'stock-report-analysis'.
    The PDF will be named 'stock_analysis.pdf'.
    """
         

    bucket_name = "smart-stock-report"
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"stock_analysis_{timestamp}.pdf"


    # Create PDF in memory with proper text wrapping and pagination
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,rightMargin=40, leftMargin=40,topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles['Title'],
        alignment=TA_CENTER,
        spaceAfter=20
    )

    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles['Heading3'],
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles['Normal'],
        alignment=TA_LEFT,
        spaceAfter=6
    )


    story = []
    
    # Add content with section headers bolded
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Detect section headers (like "1.", "2.", "3.")
        if line.startswith(("1.", "2.", "3.","4.", "5.", "6.", "Part 1:", "Part 2:", "Part 3:", "Part 4:")):
            story.append(Paragraph(line, section_style))
        else:
            story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 4))

    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)

    print("Trying to upload pdf to GCS")
    #Upload to GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.upload_from_file(pdf_buffer, content_type="application/pdf")
    public_url = f"https://storage.googleapis.com/{bucket_name}/{file_name}"
    
    # # The store_artifact method is typically an asynchronous operation
    # uri = await tool_context.artifacts.store_artifact(
    #     data=pdf_buffer.getvalue(),
    #     mime_type="application/pdf",
    #     file_name=file_name
    # )

    # bucket_path = gcs_uri.replace("gs://", "")
    # public_url = f"https://storage.googleapis.com/{bucket_path}"

    return {
        "status": "success",
        "bucket": bucket_name,
        "file_name": file_name,
        "gcs_path": f"gs://{bucket_name}/{file_name}",
        "download_url": public_url
    }


#============================ FUNCTION DEFINITION========================================================

def store_summary(project_id: str, user_id: str, stock_name: str, summary_generated: str):
    """Store summary directly into BigQuery table."""
    row = {
        "project_id": project_id,
        "user_id": user_id,
        "stock_name": stock_name,
        "summary_generated": summary_generated,
        "generated_timestamp": datetime.datetime.utcnow().isoformat()
    }

    errors = client.insert_rows_json(TABLE_ID, [row])
    if errors:
        return f"❌ Insert error: {errors}"
    return "✅ Summary stored successfully in BigQuery"

      