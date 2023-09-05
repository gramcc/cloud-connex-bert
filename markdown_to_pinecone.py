from transformers import AutoTokenizer, AutoModel
import torch
import markdown
import pinecone
import re
from config import Config

# Initialize Pinecone
pinecone.init(api_key=Config.PINECONE_API_KEY,environment=Config.PINECONE_API_ENV)
pinecone.deinit()

# Create or Connect to a Pinecone index
index_name = "test-markdown-vectors"
if index_name not in pinecone.list_indexes():
    pinecone.create_index(name=index_name, metric="cosine")

pinecone.connect(index_name)

# Initialize Huggingface Tokenizer and Model
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/paraphrase-MiniLM-L6-v2")

# Function to convert Markdown to Text
def markdown_to_text(markdown_string):
    return markdown.markdown(markdown_string)

# Function to convert Text to Vector
def text_to_vector(text):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=8000)
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings[0].numpy()

# Function to split Markdown into chunks of 1000 characters or less
def split_markdown(markdown_string, original_file_link):
    chunks = []
    subheader = None
    char_count = 0
    current_chunk = ""
    for line in markdown_string.split("\n"):
        if re.match(r"^#+ ", line):  # This is a header or subheader
            subheader = line.strip()
        line_length = len(line)
        if char_count + line_length <= 30000:
            current_chunk += line + "\n"
            char_count += line_length
        else:
            chunks.append({
                "text": current_chunk,
                "original_file_link": original_file_link,
                "latest_subheader": subheader,
                "length_characters": char_count
            })
            current_chunk = line + "\n"
            char_count = line_length
    if current_chunk:
        chunks.append({
            "text": current_chunk,
            "original_file_link": original_file_link,
            "latest_subheader": subheader,
            "length_characters": char_count
        })
    return chunks

# Sample Markdown
sample_markdown = """
# This is a title

## This is a subtitle

This is text. **This is bold text.**

* Item 1
* Item 2
"""

# Original File Link
original_file_link = "http://example.com/sample_markdown.md"

# Split the Markdown into chunks
chunks = split_markdown(sample_markdown, original_file_link)

# Convert Text to Vector and Upload to Pinecone
for i, chunk in enumerate(chunks):
    text = markdown_to_text(chunk['text'])
    vector = text_to_vector(text)
    metadata = {
        "original_file_link": chunk['original_file_link'],
        "latest_subheader": chunk['latest_subheader'],
        "length_characters": chunk['length_characters']
    }
    pinecone.upsert(ids=[f"chunk_{i}"], vectors=[vector], metadata=[metadata])

# Query Pinecone to Test
query_vector = text_to_vector("Tell me about the title and subtitle.")
query_result = pinecone.query(queries=[query_vector], top_k=1)

# Fetch the closest vector ID to the query
closest_id = query_result["results"][0]["matches"][0]["id"]
metadata = pinecone.metadata(ids=[closest_id])

# Print result
print(f"The closest document to the query is {closest_id}.")
print(f"Metadata: {metadata[closest_id]}")

# Deinitialize Pinecone
pinecone.deinit()
