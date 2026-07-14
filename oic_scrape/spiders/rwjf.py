import scrapy

from scrapy_playwright.page import PageMethod
from oic_scrape.items import AwardItem
from datetime import datetime, date
from attrs import asdict

FUNDER_ORG_NAME = "Robert Wood Johnson Foundation"
FUNDER_ORG_ROR_ID = "https://ror.org/02ymmdj85"

class RwjfSpider(scrapy.Spider):
    name = "rwjf.org_grants"

    allowed_domains = ["rwjf.org"]
    start_urls = ["https://www.rwjf.org/en/grants/awarded-grants.html"]

    def start_requests(self):
        # GET request
        yield scrapy.Request(
            "https://www.rwjf.org/en/grants/awarded-grants.html",
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("click", ".award-card-field")
                ]
            }
        )

    def parse(self, response):
        """Parse each grant page and paginate to next until finished"""

        for grant in response.css(".award-card"):
            yield grant

    def parse_grant(self, grant):
        """Parse and individual grant from the grant table"""

        grant_id = f""
        grant = AwardItem(
            grant_id=f"rwjf::{grant['grantNumber']}"
        )

        grant_title = grant.css(".data-title ::text").getall()[1]
        return grant_title
