import scrapy
from oic_scrape.items import AwardItem
from datetime import datetime, date
from attrs import asdict

FUNDER_NAME = "Institute of Museum and Library Services"
FUNDER_ROR = "https://ror.org/030prv062"


class ImlsGovSpider(scrapy.Spider):
    name = "imls.gov_grants"

    allowed_domains = ["imls.gov"]
    start_urls = ["https://www.imls.gov/grants/awarded-grants"]

    def parse(self, response):
        """
        @url https://www.imls.gov/grants/awarded-grants
        @returns requests 0 11
        @returns items 0
        Contract: should return 11 requests (up to 10 detail pages and the next index page) and no items

        """
        # Extracting the links to the grant detail pages
        for grant_link in response.css("td.views-field-title a::attr(href)").getall():
            yield response.follow(grant_link, self.parse_grant)

        # Following the pagination link
        next_page = response.css(".usa-pagination__arrow a::attr(href)").get()
        print("\nSEARCHING FOR NEXT PAGE\n\n")
        print(next_page, '\n')
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    def parse_grant(self, response):
        """
        @url https://imls.gov/grants/awarded/mh-253516-oms-23
        @returns items 1
        @returns requests 0
        @scrapes grant_id program_of_funder grant_year award_amount award_currency award_amount_usd recipient_org_name recipient_location grant_description funder_name funder_ror_id source _crawled_at
        """

        # Extract all displayed data from the page
        institution = response.css(".field--name-field-institution::text").get()
        log_number = response.css(".title--small > span::text").get()
        program = response.css(
            "div.field--name-field-program-categories-text .field__item::text"
        ).get()
        fiscal_year = response.css(
            "div.field--name-field-fiscal-year-text .field__item::text"
        ).get()
        federal_funds = response.css(
            'div.field .field__label:contains("Federal Funds") + .field__item::text'
        ).get()
        city = response.css("div.field--name-field-city .field__item::text").get()
        state = response.css("div.field--name-field-states .field__item::text").get()
        body = response.css("div.clearfix:nth-child(4)::text").get()
        # store source data
        source_data = {
            "url": response.url,
            "institution": institution,
            "log_number": log_number,
            "program": program,
            "fiscal_year": fiscal_year,
            "federal_funds": federal_funds,
            "city": city,
            "state": state,
            "body": body,
        }

        # Formatting fields
        id = f"imls:log_number::{log_number}"
        award_amount_formatted = float(federal_funds.replace("$", "").replace(",", ""))
        award_currency = "USD"  # Assuming USD for simplicity
        award_amount_usd = award_amount_formatted  # Assuming amount is already in USD
        recipient_location = f"{city}, {state}"

        # calculate fiscal year start/end date
        fy = int(fiscal_year)
        fy_start_date = date(fy - 1, 10, 1)
        fy_end_date = date(fy, 9, 30)

        comment = f"Award issued for US Federal Fiscal Year {fy}, starting on {fy_start_date} and ending on {fy_end_date}. Specific calendar year of issuance could not be determined from available data."

        # Create an instance of GrantItem
        item = AwardItem(
            _crawled_at=datetime.utcnow(),
            source="imls.gov",
            grant_id=id,
            funder_org_name=FUNDER_NAME,
            funder_org_ror_id=FUNDER_ROR,
            recipient_org_name=institution,
            recipient_org_location=recipient_location,
            grant_start_date=fy_start_date,
            grant_end_date=fy_end_date,
            award_amount=award_amount_formatted,
            award_currency=award_currency,
            award_amount_usd=award_amount_usd,
            source_url=response.url,
            grant_description=body,
            program_of_funder=program,
            comments=comment,
            raw_source_data=str(source_data),
            _award_schema_version="0.1.0",
        )

        # Return the populated item
        yield asdict(item)
