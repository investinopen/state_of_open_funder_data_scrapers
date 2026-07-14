import pytz
import scrapy
from scrapy.spiders import SitemapSpider
from datetime import datetime, date
from typing import Optional
import re
from oic_scrape.items import AwardItem, AwardParticipant

FUNDER_ORG_NAME = "James S. McDonnell Foundation"
FUNDER_ORG_ROR_ID = "https://ror.org/03dy4aq19"

class JsmfOrgSpider(SitemapSpider):
    name = "jsmf.org_grants"
    allowed_domains = ["jsmf.org"]
    sitemap_urls = ["https://www.jsmf.org/grant-sitemap.xml", "https://www.jsmf.org/grant-sitemap2.xml"]
    sitemap_rules = [("/grant/", "parse_grant_page")]

    # def parse(self, response):
        # """Parse the search results page for a given year."""
        # # Extract number of results for validation
        #
        # results_text = response.css("#showlinks p::text").get()
        # if results_text:
        #     num_results = int(re.search(r"Search Results: (\d+)", results_text).group(1))
        #
        # # Parse each grant row
        # for grant in response.xpath("//table[@class='table table-striped table-sm']/tr[position()>1]"):
        #     # Extract data from the listing
        #     grant_info = grant.css("td")[0]
        #     grant_details = grant.css("td")[1]
        #
        #     # Get the grant URL and follow to detailed page
        #     grant_url = grant_info.css("a::attr(href)").get()
        #     if grant_url:
        #         yield response.follow(
        #             grant_url,
        #             callback=self.parse_grant_page,
        #             meta={
        #                 "listing_data": {
        #                     "org_name": grant_info.css("strong::text").get(),
        #                     "researcher": grant_info.xpath(".//text()").re_first(r"\n(.*?)<br"),
        #                     "program": grant_info.xpath(".//text()").re_first(r"Program: (.*?)<br"),
        #                     "doi": grant_info.css("small a::text").get(),
        #                     "year": grant_details.xpath(".//text()").re_first(r"(\d{4})"),
        #                     "amount": grant_details.xpath(".//text()").re_first(r"\$([0-9,]+)"),
        #                     "country": grant_details.xpath(".//text()").re_first(r"\n(.*)$"),
        #                 }
        #             }
        #         )

    def parse_grant_page(self, response):
        """Parse an individual grant page."""

        id = response.css('link[rel="canonical"]::attr(href)').get()

        grant_title_area = response.css('section[aria-labelledby="grant-title"]')
        grant_title = grant_title_area.css("h1::text").get()
        grantee = grant_title_area.css('span[itemprop="recipient"]::text').get()
        amount = grant_title_area.css('meta[itemprop="amount"]::attr("content")').get()
        currency = grant_title_area.css('meta[itemprop="currency"]::attr("content")').get()
        awarded_date = grant_title_area.css('meta[itemprop="dateAwarded"]::attr("content")').get()

        grant_details = response.css('section[aria-labelledby="grant-details"]')
        pi_full_name = grant_details.css('td[itemprop="agent"]::text').get()
        program_area = grant_details.css('td[itemprop="category"]::text').get()
        grant_duration = grant_details.css('td[itemprop="duration"]::text').get()
        grant_description = grant_details.css('td[itemprop="description"]::text').get()

        award = AwardItem(
            _crawled_at=datetime.now(tz=pytz.utc),
            source="grants.jsmf.org",
            grant_id=f"jsmf:grants::{id.split('/')[-2]}",
            funder_org_name=FUNDER_ORG_NAME,
            funder_org_ror_id=FUNDER_ORG_ROR_ID,
            recipient_org_name=grantee,
            pi_name=pi_full_name,
            grant_year=int(datetime.fromisoformat(awarded_date).year),
            grant_duration=grant_duration,
            award_amount=float(amount),
            award_currency=currency if currency else "USD",
            award_amount_usd=float(amount),
            source_url=response.url,
            grant_description=grant_description if grant_description else None,
            program_of_funder=program_area,
            raw_source_data=grant_title_area.get() + grant_details.get(),
            _award_schema_version="0.1.1"
        )
        
        yield award 