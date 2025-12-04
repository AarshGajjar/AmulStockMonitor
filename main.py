
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import requests  # For sending notifications
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


@dataclass
class Product:
    alias: str
    name: str
    available: bool
    url: str
    price: float
    inventory_quantity: int = 0

    def __str__(self) -> str:
        inventory_info = (
            f" (Stock: {self.inventory_quantity})" if self.inventory_quantity > 0 else ""
        )
        status = "Available" if self.available else "Unavailable"
        return f"{self.name} ({status}){inventory_info} - ₹{self.price}"


def get_api_requests(
    driver: webdriver.Chrome,
    endpoint_filter: Optional[str] = None,
) -> List[Tuple[str, str]]:
    logs = driver.get_log("performance")
    api_requests: List[Tuple[str, str]] = []
    seen_urls: Set[str] = set()
    for entry in logs:
        try:
            message = json.loads(entry["message"])
            method = message["message"]["method"]
            params = message["message"]["params"]
            if method == "Network.responseReceived":
                url = params["response"].get("url", "")
                if url.startswith("https://shop.amul.com/api/"):
                    if (
                        endpoint_filter is None or endpoint_filter in url
                    ) and url not in seen_urls:
                        api_requests.append((params["requestId"], url))
                        seen_urls.add(url)
        except Exception:
            continue
    return api_requests


def get_response_body(
    driver: webdriver.Chrome,
    request_id: str,
) -> Optional[Dict[str, Any]]:
    try:
        result = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        if "body" in result:
            return result
        return None
    except Exception:
        return None


class AmulAPIClient:
    def __init__(self, pincode: str) -> None:
        self.pincode = pincode
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get("https://shop.amul.com/en/")
        time.sleep(0.5)

    def _create_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        # When run in GitHub Actions, Selenium Manager will automatically
        # download and manage the correct chromedriver.
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd("Network.enable", {})
        return driver

    def __del__(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass
            
    def set_store_preferences(self) -> bool:
        input_box = self.wait.until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter Your Pincode"]'))
        )
        input_box.clear()
        input_box.send_keys(self.pincode)
        result_selector = 'div.list-group-item.text-left.searchproduct-name a.searchitem-name'
        result_tile = self.wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, result_selector)))
        result_tile.click()
        self.wait.until(
            ec.invisibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter Your Pincode"]'))
        )
        confirmation = self.wait.until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "div.pincode_wrap span.ms-2.fw-semibold"))
        )
        logger.info("✅ Pin code confirmed: %s", confirmation.text)
        return True

    def get_products(self) -> List[Dict[str, Any]]:
        protein_url = "https://shop.amul.com/en/browse/protein"
        self.driver.get(protein_url)
        time.sleep(2)
        api_requests = get_api_requests(self.driver, endpoint_filter="ms.products")
        for request_id, url in api_requests:
            if 'filters[0][field]=categories' in url:
                body = get_response_body(self.driver, request_id)
                if body and "body" in body:
                    json_data = json.loads(body["body"])
                    product_list = json_data.get("data", [])
                    logger.info("Found %s protein products.", len(product_list))
                    return product_list
        logger.error("Could not find products data.")
        return []


class StockMonitor:
    def __init__(self, pincode: str, target_products: List[str], ntfy_topic: Optional[str] = None, state_file: str = 'stock_status.json'):
        self.pincode = pincode
        self.target_products = {p.lower() for p in target_products}
        self.ntfy_topic = ntfy_topic
        self.state_file = state_file
        self.stock_status: Dict[str, bool] = self._load_state()
        logger.info("Monitoring for products: %s", ", ".join(target_products) if target_products else "all protein products")

    def _load_state(self) -> Dict[str, bool]:
        """Loads the last known stock status from a file."""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                logger.info("Loaded previous stock status from %s", self.state_file)
                return state
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Could not load previous state. Starting fresh.")
            return {}

    def _save_state(self, new_state: Dict[str, bool]):
        """Saves the current stock status to a file."""
        with open(self.state_file, 'w') as f:
            json.dump(new_state, f, indent=2)
        logger.info("Saved current stock status to %s", self.state_file)

    def run_check(self):
        """Performs a single stock check, sends alerts, and saves state."""
        logger.info("Starting stock check for pincode %s", self.pincode)
        new_stock_status = self.stock_status.copy()
        try:
            client = AmulAPIClient(pincode=self.pincode)
            if not client.set_store_preferences():
                logger.error("Failed to set store preferences. Aborting check.")
                return

            products_data = client.get_products()
            if not products_data:
                logger.warning("No products found in this check.")
                # This ensures that if they become available later, an alert is sent.
                for product_name in self.target_products:
                    new_stock_status[product_name] = False
                return

            # Keep track of products seen in this run to handle products that are no longer listed
            seen_products = set()

            for product_info in products_data:
                product_name = product_info.get("name", "").lower()
                seen_products.add(product_name)

                if not self.target_products or product_name in self.target_products:
                    is_available = bool(product_info.get("available", False))
                    
                    previous_status = self.stock_status.get(product_name, False)

                    # Alert only if it was unavailable and is now available
                    if not previous_status and is_available:
                        product = Product(
                            alias=product_info.get("alias"),
                            name=product_info.get("name"),
                            available=is_available,
                            url=f"https://shop.amul.com/en/product/{product_info.get('alias')}",
                            price=product_info.get("price"),
                            inventory_quantity=product_info.get("inventory_quantity", 0),
                        )
                        self.send_alert(product)

                    new_stock_status[product_name] = is_available

            # If monitoring specific products, check if any of them disappeared from the API response
            if self.target_products:
                missing_products = self.target_products - seen_products
                for product_name in missing_products:
                    new_stock_status[product_name] = False

        except Exception as e:
            logger.error("An error occurred during stock check: %s", e, exc_info=True)
        finally:
            # Always save the latest status
            self._save_state(new_stock_status)

    def send_alert(self, product: Product):
        """Sends a notification when a product is in stock."""
        title = f"🎉 Stock Alert: {product.name} is available!"
        message = f"Price: ₹{product.price}\nStock: {product.inventory_quantity}"
        
        logger.info(title)
        logger.info(message)
        logger.info("URL: %s", product.url)

        if self.ntfy_topic:
            try:
                requests.post(
                    f"https://ntfy.sh/{self.ntfy_topic}",
                    data=message.encode('utf-8'),
                    headers={
                        "Title": title.encode('utf-8'),
                        "Click": product.url,
                        "Tags": "tada,shopping_cart"
                    }
                )
                logger.info("Sent ntfy.sh notification to topic: %s", self.ntfy_topic)
            except Exception as e:
                logger.error("Failed to send ntfy.sh notification: %s", e)


import os


def main():
    """Main function to run the stock monitor."""
    # --- Configuration is read from environment variables ---
    PINCODE = os.getenv("PINCODE", "")
    
    # TARGET_PRODUCTS should be a comma-separated string in the environment variable.
    # e.g., "amul high protein blueberry shake, 200 ml | pack of 8,amul high protein paneer, 400 g | pack of 2"
    # An empty string will monitor all products.
    target_products_str = os.getenv("TARGET_PRODUCTS", "")
    TARGET_PRODUCTS = [p.strip() for p in target_products_str.split(',') if p.strip()]
    
    # It's recommended to set NTFY_TOPIC as a secret in your GitHub repository settings.
    NTFY_TOPIC = os.getenv("NTFY_TOPIC")
    
    # --- End of Configuration ---

    if not NTFY_TOPIC:
        logger.warning("NTFY_TOPIC environment variable not set. Push notifications will be disabled.")

    monitor = StockMonitor(
        pincode=PINCODE, 
        target_products=TARGET_PRODUCTS,
        ntfy_topic=NTFY_TOPIC,
    )
    monitor.run_check()


if __name__ == "__main__":
    main()

