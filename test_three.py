# test_chat.py
import os
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_FOUNDRY_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21"
)

response = client.chat.completions.create(
    model=os.getenv("AZURE_DEPLOYMENT_NAME"),
    messages=[
        {"role": "system", "content": "You are a study planning assistant."},
        {"role": "user", "content": "Give me a 3-step plan to study for a midterm."}
    ]
)

print(response.choices[0].message.content)