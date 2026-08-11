from pathlib import Path
import os

from dotenv import load_dotenv
from openai import AzureOpenAI
from supabase import create_client


# Load root .env first
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)


EMBEDDING_DEPLOYMENT_NAME = os.getenv(
    "AZURE_EMBEDDING_DEPLOYMENT_NAME"
)

DEPLOYMENT_NAME = os.getenv(
    "AZURE_DEPLOYMENT_NAME"
)

print("Embedding deployment:", EMBEDDING_DEPLOYMENT_NAME)
print("Chat deployment:", DEPLOYMENT_NAME)

def get_course_context(course_id: str, goal: str):

    if not goal: 
        raise ValueError("Goal is required to retrieve course context.")

    results= retrieve_relevant_chunks(course_id, goal)
    contents = [r["content"] for r in results]

    return {"content_chunks": contents}
    

def extract_text_from_file(file_path: str) -> str:
    fileName = Path(file_path).suffix

    if fileName == ".txt":
        with open(file_path, 'r') as file:
            return file.read()
        
    elif fileName == ".pdf":

        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif fileName == ".docx":
        doc = Document(file_path)
        text =""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    else:
        raise ValueError(f"Unsupported file type: {fileName}. Only .txt, .pdf, and .docx are supported.")

   
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits the input text into chunks of specified size with optional overlap.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # Move start forward by chunk_size minus overlap

    return chunks


def embed_chunk(text: str) -> list[float]:

    print("Embedding deployment used:", EMBEDDING_DEPLOYMENT_NAME)

    response = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT_NAME,
        input=text
    )

    return response.data[0].embedding

def ingest_file(file_path: str, course_id: str, tag: str = "document"):
    text = extract_text_from_file(file_path)
    chunks = chunk_text(text)
    source = Path(file_path).name  

    for i, chunk in enumerate(chunks):
        embedding_vector = embed_chunk(chunk)
        
        supabase.table("course_materials").insert({
            "course_id": course_id,
            "tag": tag,
            "source": source, 
            "content": chunk,
            "embedding": embedding_vector
        }).execute()

def retrieve_relevant_chunks(course_id: str, query: str, match_count: int = 5) -> list[dict]:
    
    query_vector = embed_chunk(query)
    response = supabase.rpc("match_course_materials", {
    "query_embedding": query_vector,
    "match_course_id": course_id,
    "match_count": match_count
}).execute()
    
    return response.data or []
    
def course_has_content(course_id: str) -> bool:
    """
    Cheap existence check to see if this course has any ingested material at all. 
    """

    response = supabase.table("course_materials").select("id").eq("course_id", course_id).limit(1).execute()

    return len(response.data) > 0

# Verification Test
if __name__ == "__main__":
    print("\n--- Testing empty result case ---")
    empty_context = get_course_context("HIST2301", "What is covered on the midterm?")
    print(empty_context)