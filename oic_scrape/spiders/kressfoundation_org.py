import scrapy
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup
from oic_scrape.items import AwardItem

FUNDER_ORG_NAME = "Samuel H. Kress Foundation"
FUNDER_ORG_ROR_ID = "https://ror.org/00akqa526"

class KressFoundationSpider(scrapy.Spider):
    name = "kressfoundation.org_grants"
    allowed_domains = ["kressfoundation.org"]
    start_urls = ["https://www.kressfoundation.org/Programs/Past-Grants-Fellowships"]

    def start_requests(self):
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_token
        )

    def parse_token(self, response):
        token = response.css('input[name="__RequestVerificationToken"]::attr(value)').get()
        
        # Make first page request
        yield self.create_page_request(0, token, "pagesize")

    def create_page_request(self, page_num, token, form_type):
        datatable_settings = [
            {"name": "sEcho", "value": 1},
            {"name": "iColumns", "value": 5},
            {"name": "sColumns", "value": "Program,Grantee,Description,Amount,Year"},
            {"name": "iDisplayStart", "value": 0},
            {"name": "iDisplayLength", "value": -1},
            {"name": "mDataProp_0", "value": 0},
            {"name": "sSearch_0", "value": ""},
            {"name": "bRegex_0", "value": False},
            {"name": "bSearchable_0", "value": True},
            {"name": "mDataProp_1", "value": 1},
            {"name": "sSearch_1", "value": ""},
            {"name": "bRegex_1", "value": False},
            {"name": "bSearchable_1", "value": True},
            {"name": "mDataProp_2", "value": 2},
            {"name": "sSearch_2", "value": ""},
            {"name": "bRegex_2", "value": False},
            {"name": "bSearchable_2", "value": True},
            {"name": "mDataProp_3", "value": 3},
            {"name": "sSearch_3", "value": ""},
            {"name": "bRegex_3", "value": False},
            {"name": "bSearchable_3", "value": True},
            {"name": "mDataProp_4", "value": 4},
            {"name": "sSearch_4", "value": ""},
            {"name": "bRegex_4", "value": False},
            {"name": "bSearchable_4", "value": True},
            {"name": "sSearch", "value": ""},
            {"name": "bRegex", "value": False},
            {"name": "TableId", "value": "PASTGRANTLIST"},
            {"name": "iSortCol_0", "value": "NodeOrder"},
            {"name": "sSortDir_0", "value": "ASC"}
        ]

        pager_settings = {
            "FromRouteVars": False,
            "CurrentPage": page_num,
            "FirstListPage": 0,
            "FirstPage": 0,
            "LastListPage": 0,
            "LastPage": 1,
            "PageSize": 90,
            "TotalItems": 166,
            "TotalPages": 2,
            "Filters": [],
            "PersistentFilters": [],
            "SimpleFilters": [],
            "FormType": form_type,
            "NodeAlias": None,
            "Path": None,
            "SortBy": "NodeOrder",
            "SortDirection": "ASC"
        }

        return scrapy.Request(
            url="https://www.kressfoundation.org/Datatable/Filter",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Origin": "https://www.kressfoundation.org",
                "Referer": "https://www.kressfoundation.org/Programs/Past-Grants-Fellowships"
            },
            cookies={
                "__RequestVerificationToken": token,
            },
            body=json.dumps({
                "DatatableSettings": datatable_settings,
                "PagerSettings": pager_settings
            }),
            callback=self.parse_grants,
            meta={"token": token, "page": page_num},
            dont_filter=True
        )

    def clean_html_text(self, html_str):
        """Clean HTML string and extract text content"""
        if not html_str:
            return None
        soup = BeautifulSoup(html_str, 'html.parser')
        return soup.get_text(strip=True)

    def parse_amount(self, amount_str):
        """Parse amount string to float, with error handling"""
        try:
            if not amount_str:
                return None
            clean_amount = self.clean_html_text(amount_str)
            if not clean_amount:
                return None
            return float(re.sub(r'[^\d.]', '', clean_amount))
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Could not parse amount: {amount_str} - {str(e)}")
            return None

    def parse_grants(self, response):
        try:
            data = json.loads(response.text)
            grants = data.get("Datatable", {}).get("aaData", [])
            
            for grant in grants:
                program, grantee, description, amount, year = [
                    self.clean_html_text(field) for field in grant
                ]
                
                amount_clean = self.parse_amount(amount)
                
                if not amount_clean:
                    self.logger.warning(f"Could not parse amount for grant: {grantee}")
                    continue

                # Extract year number from string like "year2009"
                year_match = re.search(r'(\d{4})', year) if year else None
                year_clean = int(year_match.group(1)) if year_match else None

                yield AwardItem(
                    _crawled_at=datetime.utcnow(),
                    source="kressfoundation.org",
                    grant_id=f"kress:grants::{hash(f'{grantee}{amount}{year}')}",
                    funder_org_name=FUNDER_ORG_NAME,
                    funder_org_ror_id=FUNDER_ORG_ROR_ID,
                    recipient_org_name=grantee,
                    grant_year=year_clean,
                    award_amount=amount_clean,
                    award_currency="USD",
                    award_amount_usd=amount_clean,
                    source_url=self.start_urls[0],
                    grant_description=description,
                    program_of_funder=program,
                    raw_source_data=str(grant)
                )

            # Handle pagination
            current_page = response.meta["page"]
            if current_page == 0:
                token = response.meta["token"]
                yield self.create_page_request(1, token, "pager")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Response text: {response.text}")
        except Exception as e:
            self.logger.error(f"Error processing grants: {str(e)}")