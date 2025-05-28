import asyncio
import requests
import json
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime
from bs4 import BeautifulSoup
import time

async def get_article_urls(crawler, page_url):
    # Get the raw HTML
    result = await crawler.arun(url=page_url, config=CrawlerRunConfig())
    
    # Parse the HTML
    soup = BeautifulSoup(result.html, 'html.parser')

    # Find all articles with the specified class
    articles = soup.find_all('div', class_='css-1dbjc4n r-13awgt0 r-18u37iz r-1w6e6rj r-6gpygo')
    
    article_urls = []
    for article in articles:
        # Find all links within the article
        links = article.find_all('a')
        for link in links:
            if link.get('href'):
                # Make sure the URL is absolute
                url = link['href']
                if not url.startswith('http'):
                    url = f"https://www.traveloka.com{url}"
                article_urls.append(url)
    
    return article_urls

async def extract_article_content(crawler, url):
    try:
        result = await crawler.arun(url=url, config=CrawlerRunConfig())
        soup = BeautifulSoup(result.html, 'html.parser')
        
        # Find both content containers
        content_containers = soup.find_all('div', class_='css-1dbjc4n r-11yh6sk r-l0gqae')
        if len(content_containers) < 2:
            print(f"Warning: Found {len(content_containers)} content containers instead of expected 2")
            return None
        
        # Initialize article data
        article_data = {
            'metadata': {
                'url': url,
                'title': '',
                'time': ''
            },
            'content': []
        }
        
        # Process the first container (title and upload time)
        header_container = content_containers[0]
        # Find title (usually in h1)
        title = header_container.find('h1')
        if title:
            article_data['metadata']['title'] = title.get_text(strip=True)
        
        # Find upload time (get the second occurrence)
        time_elements = header_container.find_all('div', class_='css-901oao r-uh8wd5 r-ubezar r-majxgm r-135wba7 r-1b7u577 r-fdjqy7')
        if len(time_elements) >= 2:
            # Extract only the date part (before the dash)
            full_time_text = time_elements[1].get_text(strip=True)
            date_part = full_time_text.split(' - ')[0]
            article_data['metadata']['time'] = date_part
        
        # Process the second container (main content)
        content_container = content_containers[1]
        
        # Define the tags we want to extract text from
        target_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li']
        
        # Get all elements in the container
        all_elements = content_container.find_all(target_tags)
        
        # Process elements in order
        for element in all_elements:
            # Skip if this element is a child of a list (li) that we've already processed
            if element.parent and element.parent.name == 'li' and element.parent in all_elements:
                continue
                
            # Get text based on tag type
            if element.name in ['ul', 'ol']:
                # For lists, get all list items
                items = element.find_all('li', recursive=False)  # Only direct children
                if items:
                    list_text = [item.get_text(strip=True) for item in items]
                    article_data['content'].extend(list_text)
            else:
                # For other elements, get direct text
                text = element.get_text(strip=True)
                if text:
                    article_data['content'].append(text)
        
        return article_data
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return None

async def main():
    # Configure browser settings
    browser_config = BrowserConfig()
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        all_articles = []
        base_url = "https://www.traveloka.com/vi-vn/explore/destinations?page="
        
        # Loop through pages 1 to 300
        for page in range(1, 331):
            page_url = f"{base_url}{page}"
            print(f"Crawling page {page}...")
            
            try:
                urls = await get_article_urls(crawler, page_url)
                print(f"Found {len(urls)} URLs on page {page}")
                
                # Process each article URL
                for url in urls:
                    print(f"Processing article: {url}")
                    article_content = await extract_article_content(crawler, url)
                    if article_content:
                        all_articles.append(article_content)
                    
                    # Add a small delay between article requests
                    await asyncio.sleep(0.2)
                
                # Add a delay between pages
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"Error crawling page {page}: {str(e)}")
                continue
        
        # Save all articles to a JSON file
        with open("data/traveloka_articles.json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nTotal articles collected: {len(all_articles)}")
        print("Articles have been saved to traveloka_articles.json")

if __name__ == "__main__":
    asyncio.run(main()) 