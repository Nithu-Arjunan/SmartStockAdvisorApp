import vertexai
from google.adk.memory import VertexAiMemoryBankService

client = vertexai.Client(project="smart-stock-advisor", location="us-central1")

agent_engine = client.agent_engines.create(
    config={
        "context_spec": {
            "memory_bank_config": {
                "generation_config": {
                    "model": f"projects/smart-stock-advisor/locations/us-central1/publishers/google/models/gemini-2.5-flash"
                }
            }
        }
    }
)

memory_bank_service = VertexAiMemoryBankService(
    agent_engine_id=agent_engine.api_resource.name.split("/")[-1],
    project="smart-stock-advisor",
    location="us-central1",
)
