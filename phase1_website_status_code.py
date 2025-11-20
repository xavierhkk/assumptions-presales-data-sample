import pandas as pd
import numpy as np
import requests
from urllib.parse import urlparse, urljoin
import time
import os
import re
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_url(url):
    """Check if a URL is valid and properly formatted"""
    if not isinstance(url, str) or url.strip() == "" or url.lower() in ["not available", "n/a", "none", "not applicable"]:
        return False

    url = url.strip()

    # Handle common URL patterns and clean them up
    url = url.replace('https//', 'https://').replace('http//', 'http://')

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        # Check if it looks like a domain (contains a dot and no spaces)
        if '.' in url and ' ' not in url and not url.startswith('www.'):
            url = 'https://' + url
        elif url.startswith('www.'):
            url = 'https://' + url

    # Parse the URL to validate structure
    try:
        parsed = urlparse(url)
        if not parsed.netloc or len(parsed.netloc) < 3:  # Must have a valid domain
            return False

        # Check for obviously invalid patterns
        invalid_patterns = ['example.com', 'test.com', 'demo.com', 'placeholder', 'notavailable']
        if any(pattern in parsed.netloc.lower() for pattern in invalid_patterns):
            return False

        return True
    except:
        return False

def check_website_accessibility(url, timeout=10):
    """
    Check if a website is accessible and returns a successful response
    Returns: (is_accessible, status_code, error_message)
    """
    try:
        # Clean and normalize the URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Make a HEAD request first (lighter weight)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        # Try HEAD request first
        try:
            head_response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if head_response.status_code in [200, 301, 302, 307, 308]:
                return True, head_response.status_code, None
        except requests.exceptions.RequestException:
            pass  # Fall back to GET request if HEAD fails

        # Try GET request if HEAD failed
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        # Consider status codes 200-399 as successful
        if 200 <= response.status_code < 400:
            return True, response.status_code, None
        else:
            return False, response.status_code, f"Status code: {response.status_code}"

    except requests.exceptions.Timeout:
        return False, None, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error"
    except requests.exceptions.SSLError:
        # Try with verify=False as a fallback for SSL issues
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
            if 200 <= response.status_code < 400:
                return True, response.status_code, "SSL verification bypassed"
            return False, response.status_code, f"SSL error, status: {response.status_code}"
        except:
            return False, None, "SSL error"
    except requests.exceptions.RequestException as e:
        return False, None, f"Request exception: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error: {str(e)}"

def select_best_company_version_pragmatic(company_rows):
    """
    Select the best version from 5 rows of the same company using pragmatic criteria:
    1. Must have a valid website URL
    2. The website must be accessible
    """
    valid_versions = []

    for idx, row in company_rows.iterrows():
        # Get website URL
        website_url = row.get('website_url', '')

        # Check if website exists and is valid
        if pd.notna(website_url) and is_valid_url(str(website_url)):
            normalized_url = str(website_url).strip()

            # Check if website is accessible
            is_accessible, status_code, error_msg = check_website_accessibility(normalized_url)

            if is_accessible:
                # Create a copy of the row with selection metadata
                selected_row = row.copy()
                selected_row['selection_status'] = 'SELECTED'
                selected_row['website_status'] = f'Accessible (Status: {status_code})'
                selected_row['website_url_normalized'] = normalized_url
                valid_versions.append(selected_row)
            else:
                logger.debug(f"Website not accessible: {normalized_url} - {error_msg}")

    # Return the first valid version (or None if none are valid)
    if valid_versions:
        return valid_versions[0]  # Return the first valid version
    else:
        return None

def process_supplier_data_pragmatic(input_file, output_file, rejected_file=None):
    """
    Main function with pragmatic filtering criteria focusing on website validation
    """
    print("Starting Phase 1: PRAGMATIC Company Selection")
    print("=" * 60)
    print("Selection criteria:")
    print("1. Company must have a valid website URL")
    print("2. Website must be accessible and load properly")
    print("(No filtering based on company names, keywords, or complex scoring)")
    print("-" * 60)

    # Load the data
    try:
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} rows from input file")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None

    # Verify structure
    if (len(df) - 1) % 5 != 0:
        print(f"⚠️  Warning: Row count ({len(df)}) not divisible by 5 (plus header)")
        print(f"   Expected format: 1 header row + multiples of 5 company rows")

    selected_companies = []
    rejected_companies = []
    total_companies = (len(df) - 1) // 5

    print(f"\nProcessing {total_companies} companies with PRAGMATIC criteria")
    print("This will take some time as we're checking live websites...")
    print("-" * 60)

    # Process companies in blocks of 5 rows
    start_time = time.time()
    companies_processed = 0

    for i in range(1, len(df), 5):
        if i + 4 >= len(df):
            print(f"⚠️  Incomplete company block starting at row {i}, skipping")
            continue

        # Extract the 5 rows for this company
        company_block = df.iloc[i:i+5]
        company_name = company_block.iloc[0]['company_name'] if pd.notna(company_block.iloc[0]['company_name']) else f"Unnamed_{i}"

        print(f"Processing company {companies_processed + 1}/{total_companies}: {company_name}")

        # Select the best version with pragmatic criteria
        result = select_best_company_version_pragmatic(company_block)

        if result is not None:
            selected_companies.append(result)
            print(f"✅ SELECTED: {company_name} - Website accessible")
        else:
            # No valid version found - check why
            rejection_reason = "No valid website found or websites not accessible"

            # Check if any rows had websites at all
            had_websites = False
            for idx, row in company_block.iterrows():
                website_url = row.get('website_url', '')
                if pd.notna(website_url) and str(website_url).strip() != "" and str(website_url).lower() not in ["not available", "n/a", "none"]:
                    had_websites = True
                    break

            if had_websites:
                rejection_reason = "Had websites but none were accessible"
            else:
                rejection_reason = "No website information available"

            rejected_companies.append({
                'company_name': company_name,
                'rejection_reason': rejection_reason,
                'row_range': f"{i}-{i+4}"
            })
            print(f"❌ REJECTED: {company_name} - {rejection_reason}")

        companies_processed += 1

        # Rate limiting - be respectful to servers
        if companies_processed % 10 == 0:
            elapsed_time = time.time() - start_time
            avg_time_per_company = elapsed_time / companies_processed
            remaining_companies = total_companies - companies_processed
            estimated_remaining_time = avg_time_per_company * remaining_companies

            print(f"Progress: {companies_processed}/{total_companies} companies processed")
            print(f"Estimated remaining time: {estimated_remaining_time:.1f} seconds")
            print("-" * 60)

            # Brief pause every 10 companies to avoid overwhelming servers
            time.sleep(1)

    # Create output dataframe
    if selected_companies:
        result_df = pd.DataFrame(selected_companies)

        # Clean up and organize columns
        column_order = [
            'company_name', 'main_country', 'main_city', 'main_street',
            'website_url', 'website_url_normalized', 'primary_phone', 'primary_email',
            'naics_2022_primary_code', 'naics_2022_primary_label',
            'short_description', 'business_tags',
            'revenue', 'employee_count', 'year_founded',
            'selection_status', 'website_status', 'last_updated_at'
        ]

        # Ensure all columns exist and reorder
        for col in column_order:
            if col not in result_df.columns:
                result_df[col] = np.nan

        result_df = result_df[column_order]

        # Save the result
        result_df.to_csv(output_file, index=False)

        # Save rejected companies if requested
        if rejected_file and rejected_companies:
            rejected_df = pd.DataFrame(rejected_companies)
            rejected_df.to_csv(rejected_file, index=False)

        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("PHASE 1 PRAGMATIC FILTERING COMPLETE")
        print("=" * 60)
        print(f"Total processing time: {total_time:.1f} seconds")
        print(f"Total companies processed: {total_companies}")
        print(f"Companies SELECTED: {len(selected_companies)}")
        print(f"Companies REJECTED: {len(rejected_companies)}")
        print(f"Selection rate: {len(selected_companies)/total_companies:.1%}")
        print(f"\nOutput saved to: {output_file}")
        if rejected_file and rejected_companies:
            print(f"Rejected companies saved to: {rejected_file}")

        if selected_companies:
            print(f"\nSummary of selected companies:")
            print(f"- Average processing time per company: {total_time/total_companies:.2f} seconds")
            print(f"- Countries represented: {', '.join(result_df['main_country'].value_counts().head(5).index.tolist())}")
            print(f"- Top industries (NAICS):")
            for industry, count in result_df['naics_2022_primary_label'].value_counts().head(3).items():
                print(f"  • {industry}: {count} companies")

        return result_df
    else:
        print("❌ NO COMPANIES MET THE PRAGMATIC SELECTION CRITERIA!")
        print("This could mean:")
        print("1. Many companies don't have website information in the data")
        print("2. Many websites are not accessible (down, blocked, or slow)")
        print("3. The website format in the data needs cleaning")

        # Save all rejections for analysis
        if rejected_file and rejected_companies:
            rejected_df = pd.DataFrame(rejected_companies)
            rejected_df.to_csv(rejected_file, index=False)
            print(f"All rejections saved to: {rejected_file} for analysis")

        return None

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "phase1_selected_rows.csv"
    OUTPUT_FILE = "phase1_pragmatic_selected_rows.csv"
    REJECTED_FILE = "phase1_pragmatic_rejected_rows.csv"

    # Verify input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found.")
        print("Please ensure the file is in the current directory or provide the correct path.")
    else:
        # Run the pragmatic processing
        result = process_supplier_data_pragmatic(INPUT_FILE, OUTPUT_FILE, REJECTED_FILE)
