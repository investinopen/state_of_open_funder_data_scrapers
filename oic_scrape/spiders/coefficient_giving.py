import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from scrapy_playwright.page import PageMethod
from oic_scrape.items import AwardItem
from datetime import datetime, date
from attrs import asdict

FUNDER_NAME = "Coefficient Giving"
FUNDER_ROR = "https://ror.org/030prv062"


class CoefficientGivingSpider(CrawlSpider):
    name = "coefficientgiving_grants"

    allowed_domains = ["coefficientgiving.org"]
    custom_settings = {
        'HTTPCACHE_ENABLED': False,
        'DOWNLOAD_DELAY': 5,
        'DOWNLOAD_TIMEOUT': 180,
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 5
    }
    start_urls = ["https://coefficientgiving.org/funds/"]

    rules = (
        Rule(LinkExtractor(
            allow=(r"\/funds\/[\w-]{2,}\/$",)),
            callback="parse_page",
            process_request="pw_request",
            follow=True),
    )

    # async def start(self):
    #     # GET request
    #     yield scrapy.Request(
    #         "https://coefficientgiving.org/funds/",
    #         meta={
    #             "playwright": True,
    #             "playwright_include_page": True,
    #             "playwright_page_methods": [PageMethod("wait_for_load_state", "load")],
    #         },
    #         errback=self.errback_close_page
    #     )

    def pw_request(self,request, response):
        return scrapy.Request(
            url=request.url,
            callback=self.parse_page,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods":[PageMethod("wait_for_load_state", "networkidle")],
                },
            errback=self.errback_close_page
        )


    async def get_page_info(self, page):
        for i in range(5):
            val = page.viewport_size["height"]
            await page.mouse.wheel(0, val)
            await page.wait_for_timeout(5000)
        text = await page.content()

    async def parse_page(self, response):
        """
        """

        page = response.meta["playwright_page"]
        await self.get_page_info(page)
        # test = True
        # while test:

        table = (response.css('div[id="algolia-search-results"]'))
        rows = table.css('div[is="grant-table-row"]')
        program = response.xpath('//title/text()').get()
        for row in rows:
            yield self.parse_award_table(row, program=program)

        next_data_page_button = response.css('a[id="algolia-next"]')
        breaker=0
        while next_data_page_button and breaker < 2:
            print('Found next page link...following')
            await page.click(selector="#algolia-next")
            await page.wait_for_load_state('networkidle')
            print(page.locator('css=div[id="algolia-search-results"]').all_text_contents())
            # table = response.css('div[id="algolia-search-results"]')
            # rows = table.css('div[is="grant-table-row"]')
            # for row in rows:
            #     yield self.parse_award_table(row, program=program)
            
            next_data_page_button = response.css('a[id="algolia-next"]')
            c = [b.attrib["class"] for b in next_data_page_button]
            if 'pointer-events-none' in c[0]:
                next_data_page_button = None
            breaker += 1
        await page.close()


    def parse_award_table(self, row, program:str):

        cells = row.css('div::text').getall()
        # print(cells)
        try:
            # Not all orgs have a link and if they don't they get captured in a div
            org_from_link = row.css('a::text').get()
            c = [e for e in cells if not e.startswith('\n')]
            if org_from_link:
                c.insert(0, org_from_link)
            org = c[0]
            title = c[1]
            start_date = c[2]
            amount = c[3]

            award = AwardItem(
                _crawled_at=datetime.now(),
                source="coefficientgiving.org",
                grant_id=f"coefficientgiving:grants::{org}_{start_date.replace(' ', '_')}",
                funder_org_name=FUNDER_NAME,
                funder_org_ror_id=FUNDER_ROR,
                program_of_funder=program,
                grant_title=title,
                recipient_org_name=org,
                grant_year=int(start_date.split(' ')[1]),
                grant_start_date=datetime.strptime(f'1 {start_date}', "%d %B %Y").date(),
                award_amount=float(amount.removeprefix('$').replace(',','')),
                award_currency='USD',
                award_amount_usd=float(amount.removeprefix('$').replace(',','')),
                # raw_source_data=row.get(),
                _award_schema_version="0.1.0",
            )
        except IndexError as e:
            print(e)
            print(cells)
            award = AwardItem(datetime(1,1, 1), '', '', '', '')

        return award

    async def errback_close_page(self, failure):
        # Close page if request fails
        page = failure.request.meta["playwright_page"]
        await page.close()