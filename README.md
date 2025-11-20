since no clear targeting was provided but the suggestion to start from my own assumptions + subtle data from the challenge i ve decided to split the project into phases;

step 1: selection of the rows (1 per groups of 5, 2-6, 7-11..)

a. phase1_rows_scoring_selection.py

website_domain and website_url being filled is decisive

rows with highest score are being selected for the next phase (real world presence confirmation + relevance)

fields that increases the row score: phone data, address data, manufacturing relevance (by codes, keywords/tags)

b. phase1_website_status_code.py

checks if website exists and is reachable

c. another layer with phone number checks + email validation checks but since the reliable solution i ve found costs money for the number of queries i need i am just pointing it out here

https://www.ipqualityscore.com/solutions/phone-validation // https://www.ipqualityscore.com/email-verification

step 2: qualifying rows into leads - manufacturing relevance and manufacturing reliability

a. phase2_manufacturing_relevance.py

manufacturing relevance: must have relevant NAICS codes or at least 2 manufacturing keywords/tags, filter by industry codes, business descriptions

b. phase3_manufacturing_reliability.py

supplier capability assessment - evaluate company size (employee_count_type and employee_count), stability (year_founded), financials (revenue_type and revenue)

geographical and logistics analysis — consider location factors for supply chain efficiency (num_locations)
