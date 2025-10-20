"""
Advanced web scraping agent using Playwright
"""
import asyncio
import random
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse, urljoin
import json

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeout
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from utils.logger import logger
from utils.validators import validate_amazon_url, validate_proxy
from utils.helpers import generate_task_id, hash_string
from models.extraction_result import ExtractionResult, ExtractionStatus

class ScraperAgent:
    """Advanced scraper with anti-detection features"""
    
    def __init__(self, use_proxy: bool = None, headless: bool = None):
        self.use_proxy = use_proxy if use_proxy is not None else settings.use_proxy
        self.headless = headless if headless is not None else settings.scraper_headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.ua = UserAgent()
        self.current_proxy: Optional[str] = None
        self.session_id = generate_task_id("session")
        
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        """Initialize browser with anti-detection measures"""
        logger.info(f"Initializing scraper session: {self.session_id}")
        
        playwright = await async_playwright().start()
        
        # Browser launch arguments for stealth
        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        }
        
        # Add proxy if configured
        if self.use_proxy and settings.proxy_list:
            self.current_proxy = self._get_random_proxy()
            if self.current_proxy:
                launch_args["proxy"] = self._parse_proxy(self.current_proxy)
                logger.info(f"Using proxy: {self.current_proxy}")
        
        # Launch browser
        self.browser = await playwright.chromium.launch(**launch_args)
        
        # Create context with anti-detection features
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self._get_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # New York
            "color_scheme": "light",
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "java_script_enabled": True,
            "accept_downloads": False,
            "ignore_https_errors": True
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts to context
        await self._inject_stealth_scripts()
        
        # Set cookies for Amazon
        await self._set_amazon_cookies()
        
        logger.info("Scraper initialized successfully")
    
    async def _inject_stealth_scripts(self):
        """Inject JavaScript to avoid detection"""
        stealth_js = """
        // Override navigator properties
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override chrome property
        window.chrome = {
            runtime: {}
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Add mouse movement simulation
        let mouseX = 100;
        let mouseY = 100;
        
        setInterval(() => {
            mouseX += Math.random() * 10 - 5;
            mouseY += Math.random() * 10 - 5;
            
            const event = new MouseEvent('mousemove', {
                clientX: mouseX,
                clientY: mouseY
            });
            document.dispatchEvent(event);
        }, 1000);
        """
        
        await self.context.add_init_script(stealth_js)
    
    async def _set_amazon_cookies(self):
        """Set cookies to appear as returning visitor"""
        cookies = [
            {
                "name": "session-id",
                "value": f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                "domain": ".amazon.com",
                "path": "/"
            },
            {
                "name": "ubid-main",
                "value": f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                "domain": ".amazon.com",
                "path": "/"
            },
            {
                "name": "i18n-prefs",
                "value": "USD",
                "domain": ".amazon.com",
                "path": "/"
            }
        ]
        
        await self.context.add_cookies(cookies)
    
    def _get_user_agent(self) -> str:
        """Get random user agent"""
        if settings.user_agent_rotation:
            return self.ua.random
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def _get_random_proxy(self) -> Optional[str]:
        """Get random proxy from list"""
        if not settings.proxy_list:
            return None
        return random.choice(settings.proxy_list)
    
    def _parse_proxy(self, proxy: str) -> Dict[str, str]:
        """Parse proxy string to Playwright format"""
        if '@' in proxy:
            # Format: user:pass@host:port
            auth, server = proxy.split('@')
            username, password = auth.split(':')
            host, port = server.split(':')
            
            return {
                "server": f"http://{host}:{port}",
                "username": username,
                "password": password
            }
        else:
            # Format: host:port
            host, port = proxy.split(':')
            return {"server": f"http://{host}:{port}"}
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def scrape_product(self, url: str) -> ExtractionResult:
        """
        Scrape Amazon product page
        """
        task_id = generate_task_id("scrape")
        result = ExtractionResult(
            task_id=task_id,
            product_url=url,
            status=ExtractionStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        
        try:
            # Validate URL
            is_valid, asin = validate_amazon_url(url)
            if not is_valid:
                raise ValueError(f"Invalid Amazon URL: {url}")
            
            result.asin = asin
            logger.info(f"Scraping product: {asin}", task_id=task_id)
            
            # Create new page
            page = await self.context.new_page()
            
            # Add random delay to appear human
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate with retry logic
            await self._navigate_with_retry(page, url)
            
            # Wait for content to load
            await self._wait_for_content(page)
            
            # Random scroll to simulate human behavior
            await self._human_like_scroll(page)
            
            # Extract page data
            page_data = await self._extract_page_data(page)
            
            # Take screenshot for debugging
            if settings.debug:
                screenshot_path = f"tmp/screenshots/{task_id}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.debug(f"Screenshot saved: {screenshot_path}")
            
            # Get page HTML
            html_content = await page.content()
            
            # Close page
            await page.close()
            
            # Update result
            result.raw_html = html_content
            result.structured_data = page_data
            result.status = ExtractionStatus.SUCCESS
            result.progress = 100
            
            logger.info(f"Successfully scraped product: {asin}", task_id=task_id)
            
        except PlaywrightTimeout as e:
            logger.error(f"Timeout while scraping: {str(e)}", task_id=task_id)
            result.status = ExtractionStatus.FAILED
            result.errors.append({
                "code": "TIMEOUT",
                "message": str(e),
                "timestamp": datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error scraping product: {str(e)}", task_id=task_id)
            result.status = ExtractionStatus.FAILED
            result.errors.append({
                "code": "SCRAPING_ERROR",
                "message": str(e),
                "timestamp": datetime.utcnow()
            })
        
        finally:
            result.mark_completed()
            
        return result
    
    async def _navigate_with_retry(self, page: Page, url: str, max_attempts: int = 3):
        """Navigate to URL with retry logic"""
        for attempt in range(max_attempts):
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.scraper_timeout
                )
                
                # Check for blocking
                if response and response.status == 503:
                    logger.warning(f"Blocked by Amazon (503), attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    raise Exception("Blocked by Amazon anti-bot system")
                
                # Check for CAPTCHA
                if await page.query_selector("#captchacharacters"):
                    logger.warning("CAPTCHA detected")
                    # Here you could implement CAPTCHA solving
                    raise Exception("CAPTCHA requires solving")
                
                return response
                
            except PlaywrightTimeout:
                if attempt < max_attempts - 1:
                    logger.warning(f"Navigation timeout, attempt {attempt + 1}")
                    await asyncio.sleep(random.uniform(2, 5))
                else:
                    raise
    
    async def _wait_for_content(self, page: Page):
        """Wait for important content to load"""
        selectors = [
            "#productTitle",  # Product title
            ".a-price-whole",  # Price
            "#availability",  # Availability
            "#feature-bullets",  # Features
        ]
        
        # Wait for at least one important element
        await page.wait_for_selector(
            " or ".join([f"css={s}" for s in selectors]),
            timeout=10000,
            state="visible"
        )
        
        # Additional wait for dynamic content
        await page.wait_for_load_state("networkidle", timeout=5000)
    
    async def _human_like_scroll(self, page: Page):
        """Simulate human-like scrolling behavior"""
        # Get page height
        scroll_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        
        # Scroll in chunks
        current_position = 0
        while current_position < scroll_height:
            # Random scroll distance
            scroll_distance = random.randint(100, 500)
            current_position += scroll_distance
            
            # Scroll
            await page.evaluate(f"window.scrollTo(0, {current_position})")
            
            # Random pause
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Sometimes scroll back up a bit
            if random.random() < 0.2:
                back_distance = random.randint(50, 150)
                current_position -= back_distance
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                await asyncio.sleep(random.uniform(0.3, 0.7))
    
    async def _extract_page_data(self, page: Page) -> Dict[str, Any]:
        """Extract structured data from page"""
        data = {}
        
        # Define extraction rules
        extractors = {
            "title": "#productTitle",
            "price": ".a-price-whole",
            "currency": ".a-price-symbol",
            "rating": "span.a-icon-alt",
            "reviews_count": "#acrCustomerReviewText",
            "availability": "#availability span",
            "brand": "#bylineInfo",
            "features": "#feature-bullets li span",
            "images": "#altImages img",
            "description": "#productDescription",
            "details": "#detailBullets_feature_div",
            "seller": "#sellerProfileTriggerId",
            "shipping": "#mir-layout-DELIVERY_BLOCK",
            "categories": ".a-breadcrumb a"
        }
        
        for key, selector in extractors.items():
            try:
                if key in ["features", "images", "categories"]:
                    # Extract multiple elements
                    elements = await page.query_selector_all(selector)
                    if key == "images":
                        data[key] = []
                        for elem in elements[:10]:  # Limit to 10 images
                            src = await elem.get_attribute("src")
                            if src:
                                data[key].append(src)
                    else:
                        data[key] = []
                        for elem in elements:
                            text = await elem.text_content()
                            if text:
                                data[key].append(text.strip())
                else:
                    # Extract single element
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text:
                            data[key] = text.strip()
            except Exception as e:
                logger.debug(f"Failed to extract {key}: {str(e)}")
        
        # Extract additional data using JavaScript
        js_data = await page.evaluate("""
            () => {
                const getMetaContent = (name) => {
                    const meta = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                    return meta ? meta.content : null;
                };
                
                return {
                    canonical_url: document.querySelector('link[rel="canonical"]')?.href,
                    page_title: document.title,
                    meta_description: getMetaContent('description'),
                    og_image: getMetaContent('og:image'),
                    product_json: (() => {
                        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (let script of scripts) {
                            try {
                                const json = JSON.parse(script.textContent);
                                if (json['@type'] === 'Product') {
                                    return json;
                                }
                            } catch {}
                        }
                        return null;
                    })()
                };
            }
        """)
        
        data.update(js_data)
        
        return data
    
    async def scrape_search_results(self, query: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """Scrape Amazon search results"""
        results = []
        base_url = "https://www.amazon.com/s"
        
        page = await self.context.new_page()
        
        try:
            for page_num in range(1, max_pages + 1):
                # Build search URL
                search_url = f"{base_url}?k={query}&page={page_num}"
                
                logger.info(f"Scraping search page {page_num} for query: {query}")
                
                # Navigate to search page
                await self._navigate_with_retry(page, search_url)
                
                # Wait for results
                await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)
                
                # Extract product data
                products = await page.evaluate("""
                    () => {
                        const results = [];
                        const items = document.querySelectorAll('[data-component-type="s-search-result"]');
                        
                        items.forEach(item => {
                            const asin = item.getAttribute('data-asin');
                            const title = item.querySelector('h2 a span')?.textContent;
                            const url = item.querySelector('h2 a')?.href;
                            const price = item.querySelector('.a-price-whole')?.textContent;
                            const rating = item.querySelector('.a-icon-alt')?.textContent;
                            const image = item.querySelector('.s-image')?.src;
                            
                            if (asin && title) {
                                results.push({
                                    asin,
                                    title,
                                    url: url ? new URL(url, window.location.origin).href : null,
                                    price,
                                    rating,
                                    image
                                });
                            }
                        });
                        
                        return results;
                    }
                """)
                
                results.extend(products)
                
                # Random delay between pages
                if page_num < max_pages:
                    await asyncio.sleep(random.uniform(2, 5))
            
        finally:
            await page.close()
        
        logger.info(f"Found {len(results)} products for query: {query}")
        return results
    
    async def close(self):
        """Close browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        
        logger.info(f"Scraper session closed: {self.session_id}")

class ScraperPool:
    """Manage pool of scrap
