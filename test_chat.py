from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
import os
 
# Load .env
script_dir = Path(__file__).parent
load_dotenv(script_dir / ".env")
 
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)
 
print("Testing Azure connection...")
 
try:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_DEPLOYMENT_NAME"),
        messages=[
            {"role": "user", "content": "Say System Online!"}
        ]
    )
 
    print("Success:")
    print(response.choices[0].message.content)
 
except Exception as e:
    print("Failed:", e)
