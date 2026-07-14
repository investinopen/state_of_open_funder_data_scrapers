import scrapy
from scrapy.spiders import SitemapSpider
import dateparser
from datetime import datetime
from dateutil.relativedelta import relativedelta
from oic_scrape.items import AwardItem, AwardParticipant
import re
from attrs import asdict

FUNDER_ROR_ID = "https://ror.org/011x6n313"
FUNDER_NAME = "Leona M. and Harry B. Helmsley Charitable Trust"

class HelmsleyOrgSitemapSpider(SitemapSpider):
    name = "helmsley.org_grants"
    allowed_domains = ["helmsleytrust.org"]
    sitemap_urls = ["https://helmsleytrust.org/sitemap_index.xml"]
    sitemap_rules = [
        ('/grants/', 'parse_grant'),
    ]

    def parse_grant(self, response):
        self.logger.info(f"Processing grant page: {response.url}")
        
        recipient_org_name = response.css(".headline::text").get()

        award_date = self.get_item_value_from_sibling(response, "Date of Award")
        grant_duration = self.get_item_value_from_sibling(response, "Term of Grant")
        award_amount = self.get_item_value_from_sibling(response, "Amount")
        program_of_funder = self.get_item_value_from_sibling(response, "Program")
        grant_description = self.get_item_value_from_sibling(response, "Project Title")

        raw_source_data = {
            "url": response.url,
            "recipient_org_name": recipient_org_name,
            "award_date": award_date,
            "term_of_grant": grant_duration,
            "amount": award_amount,
            "project_title": grant_description,
            "program": program_of_funder,
        }

        source_url = response.url

        _match = re.search(r"(\d+)(?:/)?$", source_url)
        if _match:
            grant_id = f"helmsley:grants::{_match.group(1)}"
        else:
            self.logger.warning(f"Could not find grant ID in the URL {source_url}.")
            grant_id = f"helmsley:grants::{hash(source_url)}"  # Fallback to a hash of the URL
        
        formatted_award_amount = float(re.sub(r"[^\d.]", "", award_amount)) if award_amount else None

        grant_start_date = dateparser.parse(award_date) if award_date else None
        grant_year = int(grant_start_date.year) if grant_start_date else None

        duration_in_months = re.search(r"\d+", grant_duration) if grant_duration else None
        if duration_in_months and grant_start_date:
            duration_in_months = int(duration_in_months.group())
            grant_end_date = grant_start_date + relativedelta(months=duration_in_months)
        else:
            grant_end_date = None

        # Create an AwardParticipant for the recipient organization
        recipient = AwardParticipant(
            full_name=recipient_org_name,
            is_pi=True,  # Assuming the recipient organization is the primary recipient
            affiliations=[recipient_org_name],
            grant_role="Recipient Organization"
        )

        award = AwardItem(
            _crawled_at=datetime.utcnow(),
            source="helmsleytrust.org",
            grant_id=grant_id,
            funder_org_name=FUNDER_NAME,
            recipient_org_name=recipient_org_name,
            funder_org_ror_id=FUNDER_ROR_ID,
            pi_name=recipient_org_name,  # Using recipient org name as PI name
            named_participants=[recipient],
            grant_year=grant_year,
            grant_duration=grant_duration,
            grant_start_date=grant_start_date,
            grant_end_date=grant_end_date,
            award_amount=formatted_award_amount,
            award_currency="USD" if formatted_award_amount else None,
            award_amount_usd=formatted_award_amount,
            source_url=source_url,
            grant_description=grant_description,
            program_of_funder=program_of_funder,
            raw_source_data=str(raw_source_data),
            _award_schema_version="0.1.0"
        )

        yield asdict(award)

    def get_item_value_from_sibling(self, response, helmsley_heading):
        h6 = response.css(f"h6:contains('{helmsley_heading}')")
        if h6:
            value = h6.xpath("following-sibling::p[1]/text()").get()
            return value.strip() if value else None
        else:
            self.logger.warning(f"Could not find {helmsley_heading} on the page {response.url}.")
            return None