import os
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

# Force Python to find the .env file in the exact folder where this script lives
script_dir = Path(__file__).parent
load_dotenv(dotenv_path=script_dir / ".env")

# Initializes the connection using our shared credentials
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_FOUNDRY_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21"
)

print("📡 Attempting to connect to Microsoft Azure...")

try:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_DEPLOYMENT_NAME"),
        messages=[{"role": "user", "content": "Hi can you hear me?"}]
    )
    print("\n🚀 SUCCESS! Azure Response:", response.choices[0].message.content)
except Exception as e:
    print("\n❌ CONNECTION FAILED!")
    print("Error details:", e)