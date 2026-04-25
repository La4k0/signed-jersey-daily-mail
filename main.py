import asyncio
from playwright.async_api import async_playwright
import requests
import re
from colorama import init
import os
from dotenv import load_dotenv
from db import JerseyDB
from mail_sender import EmailSender

load_dotenv()

init(autoreset=True)

class JerseyMail:
    def __init__(self):
        self.home_page_url = os.getenv('PAGE_URL')
        self.currency_rate_api = os.getenv('CURRENCY_RATE_API')
        self.currency_rate_api_key = os.getenv('CURRENCY_RATE_API_KEY')

        self.favourite_teams = ['Liverpool']
        self.budged = 250

    async def gbp_to_eur(self):
        currency_rate_api_with_key = re.sub(r'_API_KEY_', self.currency_rate_api_key, self.currency_rate_api)

        response = requests.get(currency_rate_api_with_key).json()
        return float(response["conversion_rate"])

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.webkit.launch(headless=True)
        context = await self.browser.new_context()
        self.page = await context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.browser.close()
        await self.playwright.stop()

    async def wait_for_selector_and_click(self, xpath: str, timeout: int):
        element = self.page.locator(f'xpath={xpath}').first
        await element.wait_for(state="attached", timeout=timeout)
        await element.click()
        print(f"Clicked element with XPath: {xpath}")

    async def scrape_products(self):

        await self.page.goto(self.home_page_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await self.page.wait_for_selector(selector=f"xpath=//input[contains(@placeholder,'Search')]", timeout=15 * 1000, state='attached')
        await self.page.fill("//input[contains(@placeholder,'Search')]", "signed.*shirt")
        await self.wait_for_selector_and_click("//button[contains(@title,'Search')]", 15 * 1000)

        sorting_select_value = await self.page.locator("//*[contains(text(),'Sort By')]//following::select//option[contains(.,'Price') and contains(.,'Low to')]").get_attribute("value")
        await self.page.select_option("//*[contains(text(),'Sort By')]//following::select", sorting_select_value)

        await asyncio.sleep(2)

        in_budget = True

        while in_budget:
            await self.page.wait_for_selector(selector=f"xpath=(//span[contains(@class,'price') and not(contains(@class,'old')) and not(ancestor::span[contains(@class,'old-price')])])[last()]", timeout=15 * 1000, state='attached')
            last_price = self.page.locator(f"xpath=(//span[contains(@class,'price') and not(contains(@class,'old')) and not(ancestor::span[contains(@class,'old-price')])])[last()]")
            last_price_text = (await last_price.text_content()).strip()

            last_price_match = re.search(r'\d+(?:[.,]\d+)*', last_price_text, re.I|re.S|re.U)
            if last_price_match:
                last_price_digit = last_price_match.group(0)

                if ',' in last_price_digit:
                    last_price_digit = last_price_digit.replace(',','.')

                normalized_last_price = float(last_price_digit)

                if normalized_last_price > 250:
                    in_budget = False
                else:
                    await self.wait_for_selector_and_click("//button[contains(.,'Load More')]", 15 * 1000)
                    await asyncio.sleep(2)

        all_catalog_items_xpath = "//div[contains(@class,'catalog') and not(contains(.,'Print') and not(contains(.,'Celebration')))]"

        all_catalog_items =  self.page.locator(f"xpath={all_catalog_items_xpath}")
        all_catalog_items_count = await all_catalog_items.count()

        all_catalog_items_dict = {}

        for item in range(all_catalog_items_count):
            await self.page.wait_for_selector(selector=f"xpath=({all_catalog_items_xpath})[{item+1}]", timeout=15 * 1000, state='attached')

            sale_element = self.page.locator(f"xpath=({all_catalog_items_xpath})[{item + 1}]//*[contains(text(),'SALE')]")

            is_sale = await sale_element.count() > 0

            current_catalog_item_title_element = self.page.locator(f"xpath=({all_catalog_items_xpath})[{item+1}]//a[not(contains(@class,'photo'))]")
            current_catalog_item_title_text = (await current_catalog_item_title_element.text_content()).strip()
            current_catalog_href = (await current_catalog_item_title_element.get_attribute("href"))

            favourite_team = False
            for team in self.favourite_teams:
                if re.search(fr'{team}', current_catalog_item_title_text, re.I|re.U|re.S):
                    favourite_team = True
                    break

            current_catalog_item_price_element = self.page.locator(f"xpath=({all_catalog_items_xpath})[{item + 1}]//span[contains(@class,'price') and not(contains(@class,'old')) and not(ancestor::span[contains(@class,'old-price')])]")
            current_catalog_item_price_text = (await current_catalog_item_price_element.text_content()).strip()

            current_price_match = re.search(r'\d+(?:[.,]\d+)*', current_catalog_item_price_text, re.I | re.S | re.U)
            if current_price_match:
                current_price_digit = current_price_match.group(0)

                if ',' in current_price_digit:
                    current_price_digit = current_price_digit.replace(',', '.')

                normalized_current_price = float(current_price_digit)

                eur_gpp_rate = await self.gbp_to_eur()

                price_in_euro = normalized_current_price * eur_gpp_rate

                if price_in_euro < self.budged:
                    all_catalog_items_dict[f'Item[{item + 1}]'] = {
                        'Title': current_catalog_item_title_text,
                        'Price': f'{round(price_in_euro, 2)}€',
                        'Link': current_catalog_href,
                        'favourite_team': favourite_team,
                        'Sale': is_sale
                    }

        return all_catalog_items_dict

async def main():
    async with JerseyMail() as mail_sender:
        data = await mail_sender.scrape_products()

    db = JerseyDB()
    db.create_tables()
    db.save_items(data)
    db.close()

    mail_sender = EmailSender()
    mail_sender.get_data()
    mail_sender.send_email()

asyncio.run(main())