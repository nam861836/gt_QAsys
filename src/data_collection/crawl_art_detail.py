import asyncio
import requests
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime
from bs4 import BeautifulSoup
import time
import json

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

async def get_article_content(crawler, url):
    try:
        # Get the raw HTML
        result = await crawler.arun(url=url, config=CrawlerRunConfig())
        
        # Parse the HTML
        soup = BeautifulSoup(result.html, 'html.parser')
        
        # Get title
        title_element = soup.find('h1', class_='title')
        title = title_element.get_text(strip=True) if title_element else ""
        
        # Get time
        time_element = soup.find('span', class_='time')
        time_text = time_element.get_text(strip=True) if time_element else ""
        
        # Find the article body div
        article_body = soup.find('div', {'id': 'gallery-ctt', 'class': 'art-body', 'itemprop': 'articleBody'})
        
        paragraphs = []
        if article_body:
            # Find all paragraphs
            paragraphs = article_body.find_all('p')
            # Extract text from each paragraph
            paragraphs = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        
        return {
            'title': title,
            'time': time_text,
            'content': paragraphs
        }
    except Exception as e:
        print(f"Error getting content from {url}: {str(e)}")
        return {
            'title': "",
            'time': "",
            'content': []
        }

async def main():
    # Configure browser settings
    browser_config = BrowserConfig()
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        all_articles = []
        base_url = "https://laodong.vn/du-lich/tin-tuc?page="
        
        # Loop through pages 2 to 400
        for page in range(1, 400):
            page_url = f"{base_url}{page}"
            print(f"Crawling page {page}...")
            
            try:
                urls = await get_article_urls(crawler, page_url)
                print(f"Found {len(urls)} URLs on page {page}")
                
                # Get content for each article
                for url in urls:
                    print(f"Getting content from: {url}")
                    article_data = await get_article_content(crawler, url)
                    if article_data['content']:
                        article_data['url'] = url
                        all_articles.append(article_data)
                    # Add a small delay between article requests
                    await asyncio.sleep(0.5)
                
                # Add a small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error crawling page {page}: {str(e)}")
                continue
        
        # Save all articles to a JSON file
        with open("data/articles.json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nTotal articles collected: {len(all_articles)}")
        print("Articles have been saved to articles.json")

if __name__ == "__main__":
    asyncio.run(main()) 



