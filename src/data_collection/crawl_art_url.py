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

    # Find the div with class p-lst-articles
    articles_div = soup.find('div', class_='p-lst-articles')
    
    article_urls = []
    if articles_div:
        # Find all articles within this div
        articles = articles_div.find_all('article')
        
        # Extract URLs from each article
        for article in articles:
            link = article.find('a')
            if link and link.get('href'):
                article_urls.append(link['href'])
    
    return article_urls

async def main():
    # Configure browser settings
    browser_config = BrowserConfig()
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        all_urls = []
        base_url = "https://laodong.vn/du-lich/tin-tuc?page="
        
        # Loop through pages 2 to 400
        for page in range(2, 4):
            page_url = f"{base_url}{page}"
            print(f"Crawling page {page}...")
            
            try:
                urls = await get_article_urls(crawler, page_url)
                all_urls.extend(urls)
                print(f"Found {len(urls)} URLs on page {page}")
                
                # Add a small delay to avoid overwhelming the server
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error crawling page {page}: {str(e)}")
                continue
        
        # Save all URLs to a file
        with open("data/article_urls.txt", "w", encoding="utf-8") as f:
            for url in all_urls:
                f.write(f"{url}\n")
        
        print(f"\nTotal URLs collected: {len(all_urls)}")
        print("URLs have been saved to article_urls.txt")

if __name__ == "__main__":
    asyncio.run(main()) 


