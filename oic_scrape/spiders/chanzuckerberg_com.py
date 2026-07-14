import pytz
import scrapy
import json
from oic_scrape.items import AwardItem
import datetime

FUNDER_NAME = "Chan Zuckerberg Initiative"
FUNDER_ROR_ID = "https://ror.org/02qenvm24"

"""
V1 of scraper for the Chan Zuckerberg Initiative includes only grants listed
on https://chanzuckerberg.com/grants-ventures/grants/. This does not
include their funding through their venture investment or strategic investment arm.
It also excludes project details, such as the PI and fuller project descriptions.

While many of those details, particularly around specific scientific projects
are available on project pages, they are not in this initial implementation.
"""


class ChanzuckerbergComSpider(scrapy.Spider):
    name = "chanzuckerberg.com_grants"
    allowed_domains = ["chanzuckerberg.com"]
    start_urls = ["https://chanzuckerberg.com/wp-json/czi/v1/grants/"]

    def parse(self, response):
        timestamp = datetime.datetime.now(tz=pytz.UTC)
        r = json.loads(response.text)
        grants = r["grants"][0]

        for g in grants:
            raw_source_data = g["fields"]
            grant_id = f"chanzuckerberg::{raw_source_data['Opportunity Salesforce ID']}"

            ai = AwardItem(
                grant_id=grant_id,
                funder_org_name=FUNDER_NAME,
                funder_org_ror_id=FUNDER_ROR_ID,
                recipient_org_name=raw_source_data["Account Name"],
                grant_year = int(raw_source_data["Commitment Year"]),
                award_amount=float(raw_source_data["Amount"]),
                award_currency="USD",
                award_amount_usd=float(raw_source_data["Amount"]),
                source="chanzuckerberg.com",
                source_url="https://chanzuckerberg.com/grants-ventures/grants/",
                grant_description=raw_source_data["Grant Purpose"],
                program_of_funder='; '.join([str(s) for s in raw_source_data["Initiative"]]),
                # comments=f"funding_entity={raw_source_data['Funding Entity']}",
                _crawled_at=timestamp,
                raw_source_data=str(raw_source_data),
            )
            yield ai
