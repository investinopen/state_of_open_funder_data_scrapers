# This shell script will run all the active scrapers plus all the notebooks
# This version current as of April 2026
#
# Scrapers

poetry run scrapy crawl chanzuckerberg.com_grants -O data/202604/chanzuckerberg.com_grants.jsonl
poetry run scrapy crawl jsmf.org_grants -O data/202604/jsmf.org_grants.jsonl
poetry run scrapy crawl kressfoundation.org_grants -O data/202604/kressfoundation.org_grants.jsonl
poetry run scrapy crawl macfound.org_grants -O data/202604/macfound.org_grants.jsonl
poetry run scrapy crawl mellon.org_grants -O data/202604/mellon.org_grants.jsonl
poetry run scrapy crawl nasa_nssc_grants-O data/202604/nasa_nssc_grants.jsonl
poetry run scrapy crawl sloan.org_grants -O data/202604/sloan.org_grants.jsonl
poetry run scrapy crawl sloan.org_research-fellowships -O data/202604/sloan.org_research-fellowships.jsonl
poetry run scrapy crawl sshrc-ca -O data/202604/sshrc-ca.jsonl

# Notebooks

cd notebook_pipelines
jupyter execute arcadiafund.org.uk.ipynb
jupyter execute gatesfoundation.org.ipynb
jupyter execute imls_gov.ipynb
jupyter execute neh_gov.ipynb
jupyter execute nsf_downloads.ipynb
jupyter execute rwjf.org.ipynb
jupyter execute wellcome.org.ipynb