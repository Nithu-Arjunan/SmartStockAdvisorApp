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

## Tech Stack
 
•	Backend Framework: FastAPI

•	Agent Framework: ADK (Agent Development Kit)

•	Cloud Platform: Google Cloud Run & Cloud Storage

•	Programming Language: Python 3.10+

•	Frontend: HTML, CSS (Jinja2 templates)

## How it Works

1.	User enters a stock name or ticker via the web interface.
	
2.	Data_Analyst_Agent processes the data fom various resources.
  
3.	Trend_Analysis_Agent evaluates the historical data.
   
4.	Youtube Summary tool summarizes the public sentiments.
	
5.	The root agent aggregates all insights and generates a recommendation.
	
6.	Results are displayed in the web interface and can be saved as a PDF to GCP Storage.
    
7.	Allows users to query and retrieve current stock prices.
	
8.	Maintains memory to track discussed or purchased stocks and calculate associated profit or loss.



## Installation

```bash
1. Clone the repository:

git clone https://github.com/Nithu-Arjunan/SmartStockAdvisor.git


2.Create a virtual environment and activate it:

python -m venv .venv
source .venv/bin/activate     # Linux / Mac
.venv\Scripts\activate        # Windows

3.Install dependencies:

pip install -r requirements.txt

4.Start the FastAPI server:

uvicorn main:app --reload


