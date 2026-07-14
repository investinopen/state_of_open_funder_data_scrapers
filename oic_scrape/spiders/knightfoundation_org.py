import scrapy
import json
from datetime import datetime

from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError

from oic_scrape.items import AwardItem, AwardParticipant
import logging
from urllib.parse import urlparse, parse_qs

class KnightFoundationSpider(scrapy.Spider):
    name = "knightfoundation.org_grants"
    allowed_domains = ["knightfoundation.org"]
    start_urls = ["https://knightfoundation.org/wp-json/knight-foundation-app/v1/grants?per_page=100&page=1&_locale=user"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'ROBOTSTXT_OBEY': False,  # API endpoint
        'LOG_LEVEL': 'DEBUG',
    }
        
    # Define headers at the class level
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_records = 0
        self.max_pages = 52  # Set maximum number of pages to scrape
        
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse,
                errback=self.handle_error,
                dont_filter=True
            )

    def parse(self, response):
        try:
            grants = json.loads(response.text)
            
            # Stop if no grants are returned
            if not grants:
                self.logger.info("No more grants found. Stopping pagination.")
                return
            
            # Parse current_page safely
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            current_page = int(query_params.get('page', [1])[0])
            
            self.logger.info(f"Processing page {current_page}")
            self.logger.info(f"Number of grants in current response: {len(grants)}")
            
            # Process each grant
            for grant in grants:
                yield self.parse_grant(grant)
                
            # Continue pagination if current_page is less than max_pages
            if current_page < self.max_pages:
                next_page = current_page + 1
                query_params['page'] = [str(next_page)]
                new_query = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
                next_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
                self.logger.info(f"Moving to next page: {next_page}")
                yield scrapy.Request(
                    next_url,
                    headers=self.headers,
                    callback=self.parse,
                    errback=self.handle_error,
                    dont_filter=True
                )
            else:
                self.logger.info(f"Stopping pagination: reached maximum page limit of {self.max_pages}")
                    
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.logger.error("Traceback:", exc_info=True)

    def parse_grant(self, grant):
        # Extract comments if any special conditions exist
        comments = []
        if grant.get('challenges'):
            comments.append(f"challenges: {', '.join(grant['challenges'])}")
            
        # Create AwardParticipant objects for grantees
        named_participants = [
            AwardParticipant(
                full_name=grantee['post_title'],
                grant_role="Grantee",
                identifiers={"post_id": str(grantee['ID'])}
            )
            for grantee in grant['grantees']
        ]
            
        # Parse start date if available
        grant_start_date = None
        if grant.get('started_on'):
            grant_start_date = datetime.strptime(grant['started_on'], "%Y-%m-%dT%H:%M:%S%z").date()

        # Create AwardItem with all fields set at initialization
        return AwardItem(
            _crawled_at=datetime.utcnow(),
            source="Knight Foundation",
            grant_id=f"knight_foundation::{grant['id']}",
            funder_org_name="John S. and James L. Knight Foundation",
            funder_org_ror_id="https://ror.org/00mn6be63",
            recipient_org_name=grant['grantees'][0]['post_title'] if grant['grantees'] else "Unknown",
            
            # Optional fields
            grant_title=grant['name'],
            grant_description=grant['description'],
            award_amount=float(grant['amount']) if grant['amount'] else None,
            award_amount_usd=float(grant['amount']) if grant['amount'] else None,
            award_currency='USD',
            grant_start_date=grant_start_date,
            grant_year=grant_start_date.year if grant_start_date else None,
            program_of_funder='>'.join([program['name'] for program in grant.get('programs', [])]),
            comments=' | '.join(comments) if comments else None,
            named_participants=named_participants,
            raw_source_data=json.dumps(grant),
            source_url=f"https://knightfoundation.org/grants/{grant['slug']}/",
            recipient_org_location=', '.join(grant['communities']) if grant.get('communities') else None
        )

    def handle_error(self, failure):
        self.logger.error(f'Request failed: {failure.value}')
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error(f'HTTP Error on {response.url}: {response.status}')
        elif failure.check(TimeoutError, DNSLookupError, ConnectionRefusedError):
            request = failure.request
            self.logger.error(f'Network error on {request.url}')