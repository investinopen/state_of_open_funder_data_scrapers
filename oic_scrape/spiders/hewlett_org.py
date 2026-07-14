import scrapy
from scrapy.spiders import SitemapSpider
from oic_scrape.items import AwardItem
from datetime import datetime, date
import re

FUNDER_ORG_NAME = "William and Flora Hewlett Foundation"
FUNDER_ORG_ROR_ID = "https://ror.org/04hd1y677"

class HewlettOrgSpider(SitemapSpider):
    name = "hewlett.org_grants"
    allowed_domains = ["hewlett.org"]
    sitemap_urls = ["https://hewlett.org/sitemap.xml"],
    sitemap_rules = [("/grants/", "parse_grant")]

    def parse_grant(self, response):
        crawl_ts = datetime.utcnow()

        # Extract grant details with error handling
        recipient_org_name = response.css("h1::text").get(default="").strip()
        grant_title = response.css("h3.large-subtitle::text").get(default="").strip()
        
        # Extract and process amount
        amount_str = response.css('.highlight:contains("Amount") .highlights-value::text').get(default="")
        try:
            award_amount = float(amount_str.replace("$", "").replace(",", ""))
        except ValueError:
            award_amount = None
            self.logger.warning(f"Could not parse award amount: {amount_str}")

        # Extract and process date
        date_str = response.css('.highlight:contains("Date Awarded") .highlights-value::text').get(default="")
        try:
            grant_start_date = datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            grant_start_date = None
            self.logger.warning(f"Could not parse grant start date: {date_str}")

        # Extract duration
        duration_str = response.css('.highlight:contains("Term") .highlights-value::text').get(default="").strip()
        grant_duration = duration_str

        # Extract program
        program_of_funder = response.css('.highlight:contains("Program") .highlights-value a::text').get(default="").strip()

        # Extract strategies
        strategies = response.css('.highlight-strategy-link::text').getall()
        if strategies:
            program_of_funder += " > " + " > ".join(strategies)

        # Extract grant description
        grant_description = response.css('.grant-overview::text').get(default="").strip()

        # Extract grantee website and location
        grantee_website = response.css('.aboutgrantee-extra-value::attr(href)').get(default="")
        recipient_org_location = response.css('.aboutgrantee-address::text').get(default="").strip()

        # Generate a unique grant ID
        grant_id = f"hewlett:grants::{response.url.split('/')[-2]}"

        award = AwardItem(
            _crawled_at=crawl_ts,
            source="hewlett.org",
            grant_id=grant_id,
            funder_org_name=FUNDER_ORG_NAME,
            funder_org_ror_id=FUNDER_ORG_ROR_ID,
            recipient_org_name=recipient_org_name,
            recipient_org_location=recipient_org_location,
            grant_year=grant_start_date.year if grant_start_date else None,
            grant_duration=grant_duration,
            grant_start_date=grant_start_date,
            award_amount=award_amount,
            award_currency="USD" if award_amount else None,
            award_amount_usd=award_amount,
            source_url=response.url,
            grant_title=grant_title,
            grant_description=grant_description,
            program_of_funder=program_of_funder,
            raw_source_data=str({
                "url": response.url,
                "recipient_org_name": recipient_org_name,
                "grant_title": grant_title,
                "amount": amount_str,
                "date_awarded": date_str,
                "duration": duration_str,
                "program": program_of_funder,
                "description": grant_description,
                "grantee_website": grantee_website,
                "recipient_org_location": recipient_org_location
            }),
            _award_schema_version="0.1.0"
        )

        yield award