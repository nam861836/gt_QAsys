import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime
import re

# Load environment variables
load_dotenv()


def standardize_time(time_str):
    """Convert time string to DD/MM/YYYY format"""
    try:
        if " " in time_str and len(time_str.split()) == 3:
            try:
                # Try short month name first
                dt = datetime.strptime(time_str, "%d %b %Y")
            except:
                # Try full month name
                dt = datetime.strptime(time_str, "%d %B %Y")
        else:
            dt = datetime.strptime(time_str, "%d/%m/%Y")
        return dt.strftime("%d/%m/%Y")
    except:
        return time_str

def process_traveloka_articles():
    # Process traveloka_articles.json
    with open("./data/traveloka_articles.json", "r", encoding="utf-8") as f:
        traveloka_articles = json.load(f)
    
    processed_articles = []
    for article in traveloka_articles:
        # Create processed article
        processed_article = {
            "metadata": {
                "title": article.get('title'),
                "time": standardize_time(article.get('time', '')),
                "url": article.get('url')
            },
            "content": article.get('content')
        }
        processed_articles.append(processed_article)
    
    # Save processed articles to a new JSON file
    with open("./data/traveloka_articles_processed.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    process_traveloka_articles()
    print("Traveloka articles processed and saved to traveloka_articles_processed.json successfully!") 