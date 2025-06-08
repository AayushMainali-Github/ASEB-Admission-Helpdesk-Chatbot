import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import time
import re
from collections import deque
import logging
import random
import json
from fake_useragent import UserAgent
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AmritaScraper:
    def __init__(self, start_url, max_depth=5):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited_urls = set()
        self.queue = deque([(start_url, 0)])
        self.base_domain = urlparse(start_url).netloc
        self.output_file = "amrita_content.txt"
        self.session = requests.Session()
        self.ua = UserAgent()
        self.update_headers()
        self.existing_content_hashes = set()
        self.load_existing_content()
        
        self.important_keywords = {
            'academic', 'program', 'course', 'admission', 'research', 'faculty',
            'department', 'school', 'college', 'university', 'education', 'study',
            'degree', 'bachelor', 'master', 'phd', 'doctorate', 'scholarship',
            'campus', 'student', 'faculty', 'professor', 'lecturer', 'curriculum',
            'syllabus', 'examination', 'result', 'placement', 'career', 'job',
            'internship', 'project', 'thesis', 'publication', 'conference',
            'seminar', 'workshop', 'event', 'news', 'announcement', 'notice'
        }
        
        self.bangalore_keywords = {
            'bangalore', 'bengaluru', 'amrita bangalore', 'amrita bengaluru',
            'bangalore campus', 'bengaluru campus', 'amrita school of engineering bangalore',
            'amrita school of business bangalore', 'amrita bangalore campus'
        }

    def load_existing_content(self):
        """Load existing content hashes from file."""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Split content by separator
                sections = content.split('=' * 80)
                for section in sections:
                    if section.strip():
                        # Get content part (after URL)
                        content_part = section.split('\n\n', 1)[-1].strip()
                        if content_part:
                            # Create hash of content
                            content_hash = hashlib.md5(content_part.encode()).hexdigest()
                            self.existing_content_hashes.add(content_hash)
        except FileNotFoundError:
            pass

    def get_content_hash(self, content):
        """Get MD5 hash of content."""
        return hashlib.md5(content.encode()).hexdigest()

    def normalize_url(self, url):
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')
            query_params = []
            if parsed.query:
                params = dict(param.split('=') for param in parsed.query.split('&') if '=' in param)
                if 'id' in params:
                    query_params.append(f"id={params['id']}")
                if 'page' in params:
                    query_params.append(f"page={params['page']}")
            
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                '&'.join(query_params) if query_params else '',
                ''
            ))
            
            return normalized.lower()
        except:
            return url.lower()

    def update_headers(self):
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        })

    def is_bangalore_related(self, url, text=""):
        combined_text = (url + " " + text).lower()
        return any(keyword in combined_text for keyword in self.bangalore_keywords)

    def is_valid_url(self, url):
        try:
            parsed = urlparse(url)
            url_lower = url.lower()
            
            if self.is_bangalore_related(url):
                return (
                    parsed.netloc == self.base_domain and
                    not url.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip', '.doc', '.docx', '.css', '.js')) and
                    '#' not in url and
                    'mailto:' not in url and
                    'tel:' not in url and
                    'javascript:' not in url
                )
            
            has_important_keyword = any(keyword in url_lower for keyword in self.important_keywords)
            
            return (
                parsed.netloc == self.base_domain and
                not url.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip', '.doc', '.docx', '.css', '.js')) and
                '#' not in url and
                'mailto:' not in url and
                'tel:' not in url and
                'javascript:' not in url and
                has_important_keyword
            )
        except:
            return False

    def is_important_content(self, text, url=""):
        text_lower = text.lower()
        
        if self.is_bangalore_related(url, text):
            return True
            
        if len(text) < 50:
            return False
            
        keyword_count = sum(1 for keyword in self.important_keywords if keyword in text_lower)
        if keyword_count < 2:
            return False
            
        unimportant_patterns = [
            r'copyright © \d{4}',
            r'all rights reserved',
            r'privacy policy',
            r'terms of use',
            r'cookie policy',
            r'follow us on',
            r'connect with us',
            r'quick links',
            r'contact us',
            r'feedback',
            r'sitemap'
        ]
        
        if any(re.search(pattern, text_lower) for pattern in unimportant_patterns):
            return False
            
        return True

    def extract_text(self, soup, url=""):
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript", 
                           "form", "button", "input", "select", "option", "meta", "link"]):
            element.decompose()
        
        main_content = []
        
        content_containers = soup.find_all(['article', 'main', 'section', 'div'], 
                                         class_=lambda x: x and any(term in str(x).lower() 
                                         for term in ['content', 'main', 'article', 'body']))
        
        if not content_containers:
            content_containers = [soup]
            
        for container in content_containers:
            text = container.get_text(separator='\n', strip=True)
            
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            if text and self.is_important_content(text, url):
                main_content.append(text)
        
        return '\n\n'.join(main_content)

    def save_content(self, url, content):
        if not content.strip():
            return
            
        # Check if content is already in file
        content_hash = self.get_content_hash(content)
        if content_hash in self.existing_content_hashes:
            logging.info(f"Skipping duplicate content from {url}")
            return
            
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"URL: {url}\n")
            if self.is_bangalore_related(url, content):
                f.write("BANGALORE CAMPUS CONTENT\n")
            f.write(f"{'='*80}\n\n")
            f.write(content)
            f.write("\n\n")
            
        # Add hash to existing content set
        self.existing_content_hashes.add(content_hash)

    def get_page(self, url):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.update_headers()
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                if 'text/html' in response.headers.get('Content-Type', ''):
                    return response.text
                else:
                    logging.warning(f"Non-HTML content received from {url}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(random.uniform(2, 5))
        return None

    def crawl(self):
        while self.queue:
            url, depth = self.queue.popleft()
            normalized_url = self.normalize_url(url)
            
            if depth > self.max_depth or normalized_url in self.visited_urls:
                continue
                
            self.visited_urls.add(normalized_url)
            logging.info(f"Crawling: {url} (Depth: {depth})")
            
            content = self.get_page(url)
            if not content:
                continue
                
            try:
                soup = BeautifulSoup(content, 'html.parser')
                
                text_content = self.extract_text(soup, url)
                if text_content.strip():
                    self.save_content(url, text_content)
                
                if depth < self.max_depth:
                    for link in soup.find_all('a', href=True):
                        next_url = urljoin(url, link['href'])
                        normalized_next_url = self.normalize_url(next_url)
                        
                        if (self.is_valid_url(next_url) and 
                            normalized_next_url not in self.visited_urls):
                            if self.is_bangalore_related(next_url):
                                self.queue.appendleft((next_url, depth + 1))
                            else:
                                self.queue.append((next_url, depth + 1))
                            
            except Exception as e:
                logging.error(f"Error processing {url}: {str(e)}")
                continue

def main():
    start_url = "https://www.amrita.edu/"
    scraper = AmritaScraper(start_url, max_depth=5)
    
    # Don't clear the file, just append new content
    logging.info("Starting to crawl Amrita University website...")
    scraper.crawl()
    logging.info(f"Crawling completed. Content saved to {scraper.output_file}")
    logging.info(f"Total pages crawled: {len(scraper.visited_urls)}")

if __name__ == "__main__":
    main()