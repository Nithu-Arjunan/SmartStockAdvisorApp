# SmartStockAdvisorApp


SmartStockAdvisor is an AI-driven platform designed to help traders and investors make informed decisions by analysing quantitative data (historical trends) and qualitative data (financial news, YouTube insights).
The system uses ADK agents for modular intelligence and is deployed on Google Cloud Platform (GCP) for scalability and reliability.

## Key Features

•	Autonomous AI Agents: Specialized agents for data analysis and trend evaluation.

•	YouTube & News Integration: Extracts insights and sentiment from financial content.

•	Data-Driven Recommendations: Combines analysis and trend detection for actionable advice.

•	Cloud-Native Deployment: Scalable deployment using Google Cloud Run.

•	PDF Report Generation: Results can be saved to GCP Storage.

•	User-Friendly Interface: FastAPI backend with responsive HTML templates.

•	BiqQuery:Final summary generated is stored in BigQuery.

## Architecture

<img width="728" height="728" alt="image" src="https://github.com/user-attachments/assets/0962cddf-5bce-4729-80ec-56b02d97ed54" />



## Tech Stack
 
| **Category**             | **Technology Used**                       |
| ------------------------ | ----------------------------------------- |
| **Backend Framework**    | FastAPI                                   |
| **Agent Framework**      | ADK (Agent Development Kit)               |
| **Cloud Platform**       | Google Cloud Run, Cloud Storage, BigQuery |
| **Programming Language** | Python 3.10+                              |
| **Frontend**             | HTML, CSS (Jinja2 templates)              |


## How it Works

1.	User enters a stock name or ticker via the web interface.
	
2.	Data_Analyst_Agent processes the data fom various resources.
  
3.	Trend_Analysis_Agent evaluates the historical data.
   
4.	Youtube Summary tool summarizes the public sentiments.
	
5.	The root agent aggregates all insights and generates a recommendation.
	
6.	Results are displayed in the web interface and can be saved as a PDF to GCP Storage.
    
7.	Allows users to query and retrieve current stock prices.
	
8.	Maintains memory to track discussed or purchased stocks and calculate associated profit or loss.

## Project Folder Structure

```bash
SmartStockAdvisor/
│
├── main.py
├── requirements.txt
│
├── agent/
│   └── SmartStockAdvisorAgent/
│       ├── __init__.py
│       ├── agent.py
│       ├── prompt.py
│       ├── tools.py
│       └── SubAgents/
│           ├── Data_Analyst_Agent/
│           │   ├── __init__.py
│           │   ├── agent.py
│           │   └── prompt.py
│           └── Trend_Analysis_Agent/
│               ├── __init__.py
│               ├── agent.py
│               └── prompt.py
│
├── templates/
│   ├── chat.html
│   └── login.html
│
└── static/
    └── style.css
```
   


## Installation


1. Clone the repository:
```bash
git clone https://github.com/Nithu-Arjunan/SmartStockAdvisorApp.git
cd SmartStockAdvisor

```
2.Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate     # Linux / Mac
.venv\Scripts\activate        # Windows
```
3.Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

Before running the application, you need to set up your API keys and environment variables.
These are essential for authentication and integration with external services.


Create a .env file in the project root directory:

```bash
touch .env
```
Add the following keys to .env:
```bash
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_your_gcp_service_account.json
GCP_BUCKET_NAME=your_storage_bucket_name
BIGQUERY_DATASET=your_bigquery_dataset_name
BIGQUERY_TABLE=your_bigquery_table_name
```

4.Start the FastAPI server:
```bash
uvicorn main:app --reload
```
### Run the Application

Once the environment variables are configured, start the FastAPI server:
```bash
uvicorn main:app --reload
```
Open your browser and navigate to:
```bash
http://127.0.0.1:8000
```

