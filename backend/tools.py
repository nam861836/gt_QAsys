import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

def web_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Search the web using DuckDuckGo API
    """
    try:
        # Using DuckDuckGo API
        search_url = f"https://api.duckduckgo.com/?q={query}&format=json"
        response = requests.get(search_url)
        data = response.json()
        
        results = []
        if "Abstract" in data and data["Abstract"]:
            results.append({
                "title": data["Heading"],
                "snippet": data["Abstract"],
                "url": data["AbstractURL"]
            })
        
        if "RelatedTopics" in data:
            for topic in data["RelatedTopics"][:num_results-1]:
                if "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic["Text"].split(" - ")[0],
                        "snippet": topic["Text"],
                        "url": topic["FirstURL"]
                    })
        
        return results
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return []

def get_weather(city: str) -> Dict:
    """
    Get weather information using OpenWeatherMap API
    """
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            raise ValueError("OpenWeather API key not found")
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=vi"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code != 200:
            raise ValueError(f"City not found: {city}")
        
        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"]
        }
    except Exception as e:
        print(f"Error getting weather: {str(e)}")
        return None

def format_weather_context(weather_info: Dict) -> str:
    """
    Format weather information as context for the chat
    """
    if not weather_info:
        return "Không thể lấy thông tin thời tiết."
    
    return f"""Thông tin thời tiết tại {weather_info['city']}:
- Nhiệt độ: {weather_info['temperature']}°C
- Mô tả: {weather_info['description']}
- Độ ẩm: {weather_info['humidity']}%
- Tốc độ gió: {weather_info['wind_speed']} m/s"""

def format_web_search_context(search_results: List[Dict]) -> str:
    """
    Format web search results as context for the chat
    """
    if not search_results:
        return "Không tìm thấy kết quả tìm kiếm phù hợp."
    
    context = "Kết quả tìm kiếm trên web:\n\n"
    for i, result in enumerate(search_results, 1):
        context += f"{i}. {result['title']}\n"
        context += f"   {result['snippet']}\n"
        context += f"   Nguồn: {result['url']}\n\n"
    
    return context 