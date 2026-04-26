from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
# Initialize Mistral with your key and preferred model
llm = ChatMistralAI(
    model="mistral-large-latest", # Or "mistral-small-latest"
    mistral_api_key=api_key,
    temperature=0
)

# The syntax to invoke is exactly the same
response = llm.invoke("Hello, world!")
print(response.content)
