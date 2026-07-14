from typing import Dict, List, Optional
import scrapy
import json
from oic_scrape.items import AwardItem
from datetime import datetime, timezone

# NOTE: In the current iteration, this scraper does not handle multiple-listing grant pages
# Examples:
# - https://www.dorisduke.org/grants/what-weve-funded/Grant-Recipients/Talented-Students-in-the-Arts-Initiative----Leading-National-Performing-Arts--Training-Institutions1/
# - https://www.dorisduke.org/grants/what-weve-funded/Grant-Recipients/sickle-cell-diseaseadvancing-cures/
# - https://www.dorisduke.org/grants/what-weve-funded/Grant-Recipients/2020-doris-duke-artist-awards/


FUNDER_ORG_NAME = "Doris Duke Charitable Foundation"
FUNDER_ORG_ROR_ID = "https://ror.org/04n65rp89"

class DorisdukeOrgSpider(scrapy.Spider):
    name = "dorisduke.org_grants"
    source_name = "dorisduke.org"
    source_type = "grants"
    allowed_domains = ["dorisduke.org"]
    start_urls = ["https://www.dorisduke.org/grants/what-weve-funded/"]

    def get_grants(self,response) -> Optional[List[Dict]]:
        """
        Returns the list of grants on a Dorris Duke What We've Funded page

        Grant categories / subcategories are only visible on the indexes and need to be collected
        https://www.dorisduke.org/grants/what-weve-funded/
        https://www.dorisduke.org/grants/what-weve-funded/?1=1&GrantProgramID=5&GrantInitiativeID=0&GrantDate=0&GrantShow=12&GrantSortBy=0#grant-filter
        """
        scripts = response.css('script::text').getall()
        grants = []
        for script in scripts:
            if '\\"grants\\":' in script:
                script_content = script
                # grants.append(json.loads(script_content))
        # Extract the relevant portion of the JavaScript
                start_index = script_content.find('\\"grants\\":') + len('\\"grants\\":')
                end_index = script_content.rfind('\\"}]') + len('\\"}]')  # Assuming '}]}]\n' marks the end consistently
                print(f"Start index: {start_index}, End index: {end_index}")
                json_text = script_content[start_index:end_index].replace('\\"', '"')
                # json_data = json.loads(json_data)
                # grants.append(json_data)
                try:
                    grants.extend(json.loads(json_text))
                except json.decoder.JSONDecodeError as e:
                    if json_text.endswith(',"children":"$L2b"}]'):
                        json_text = json_text.replace(',"children":"$L2b"}]', '')
                        grants.extend(json.loads(json_text))
                    else: print(e)

        # Load the grants as json
        # grants = json.loads(json_data)
        return grants if grants else None
    
    
    def parse(self, response):

        # get our main list of all grants
        all_grants = self.get_grants(response)
  

        # Process the grants
        if all_grants:
            for grant in all_grants:
                yield self.parse_grant(grant)
            
    def parse_grant(self, grant):
        crawl_ts = datetime.now(tz=timezone.utc)
        source_data = {}
        source_data['url'] = grant.get('Current URL')
        source_data['recipient_org_name'] = grant.get('Organization Name')

        # award_content = grant.get('Description')
        # content_paragraphs = award_content.css('p')

        source_data['awarded_on'] = grant.get('Date')
        source_data['duration'] = grant.get('Duration')

        # description = ""
        # for paragraph in content_paragraphs[2:-1]:
        #     paragraph_text = paragraph.css('::text').get()
        #     if paragraph_text:
        #         description += paragraph_text.strip() + " "
        # if len(description) > 1:
        #     description = description.strip()
        
        source_data['description'] = grant.get('Description')
        source_data['program'] = grant.get('Program')

        source_data['project_url'] = grant.get('Grantee Site')

        # Format fields
        date_str = source_data['awarded_on'].replace("Awarded: ", "")
        start_date = datetime.strptime(date_str, "%Y-%m-%d")

        source_data['amount_str'] = grant.get('Amount')
        try:
            award_amount = float(source_data['amount_str'].replace("$", "").replace(",", ""))
        except ValueError as e:
            if source_data['amount_str'].endswith('million'):
                award_amount = float(source_data['amount_str'].replace("$", "").replace(" million", ""))*1e6
            else:
                print('ValueError:', e)
                award_amount = 0.0

        duration = source_data['duration']

        award = AwardItem(
            _crawled_at = crawl_ts,
            grant_id = f"dorisduke:grants::{grant.get('Current URL')}",
            funder_org_name = FUNDER_ORG_NAME,
            funder_org_ror_id = FUNDER_ORG_ROR_ID,
            recipient_org_name = source_data['recipient_org_name'],
            grant_year = start_date.year,
            grant_duration = duration,
            grant_start_date = start_date,
            award_amount = award_amount,
            award_currency = "USD",
            award_amount_usd = award_amount,
            source = "dorrisduke.org",
            source_url = source_data['url'],
            grant_description = source_data['description'],
            program_of_funder=source_data['program'],
            raw_source_data=grant
        )

        return award
        
