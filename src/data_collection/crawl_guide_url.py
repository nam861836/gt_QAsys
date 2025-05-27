import asyncio
import requests
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

async def main():
    # Configure browser settings
    browser_config = BrowserConfig()
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        all_urls = []
        base_url = "https://www.traveloka.com/vi-vn/explore/destinations?page="
        
        # Loop through pages 1 to 400
        for page in range(1, 3):
            page_url = f"{base_url}{page}"
            print(f"Crawling page {page}...")
            
            try:
                urls = await get_article_urls(crawler, page_url)
                all_urls.extend(urls)
                print(f"Found {len(urls)} URLs on page {page}")
                
                # Add a small delay to avoid overwhelming the server
                await asyncio.sleep(2)  # Increased delay for Traveloka
                
            except Exception as e:
                print(f"Error crawling page {page}: {str(e)}")
                continue
        
        # Save all URLs to a file
        with open("data/traveloka_urls.txt", "w", encoding="utf-8") as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        print(f"\nTotal URLs collected: {len(all_urls)}")
        print("URLs have been saved to traveloka_urls.txt")

if __name__ == "__main__":
    asyncio.run(main())