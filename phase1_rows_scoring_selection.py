import pandas as pd
import numpy as np
import os
import re

def detect_website_fields(df):
    """Detect which columns might contain website information"""
    potential_website_columns = []
    website_patterns = ['website', 'url', 'domain', 'web', 'http', 'www']

    for column in df.columns:
        column_lower = column.lower()
        if any(pattern in column_lower for pattern in website_patterns):
            potential_website_columns.append(column)

    return potential_website_columns

def has_website_data_simple(row, website_columns):
    """
    Simple check for website presence - much more permissive
    Only requires non-empty value in any website-related field
    """
    for column in website_columns:
        if column not in row.index:
            continue

        value = row[column]
        if pd.isna(value) or not isinstance(value, str):
            continue

        cleaned_value = str(value).strip()
        if cleaned_value == "":
            continue

        # Skip obvious placeholder values
        placeholder_values = ["not available", "n/a", "none", "not applicable", "no website", "www."]
        if cleaned_value.lower() in placeholder_values:
            continue

        # Accept almost anything that looks like it could be a website
        return True, column, cleaned_value

    return False, None, None

def has_phone_data(row):
    """Check if a row has valid phone data"""
    phone_columns = ['primary_phone', 'phone_numbers', 'phone', 'contact_phone']

    for column in phone_columns:
        if column not in row.index:
            continue

        value = row[column]
        if pd.notna(value) and isinstance(value, str) and value.strip() != "":
            return True

    return False

def has_address_data(row):
    """Check if a row has valid address/location data"""
    address_columns = ['main_country', 'main_city', 'main_street', 'country', 'city', 'street', 'address']

    valid_fields = 0
    for column in address_columns:
        if column not in row.index:
            continue

        value = row[column]
        if pd.notna(value) and isinstance(value, str) and value.strip() != "":
            valid_fields += 1
            if valid_fields >= 2:  # At least 2 address fields should be filled
                return True

    return False

def check_manufacturing_relevance(row):
    """Check if a row has manufacturing relevance through NAICS codes or keywords"""
    # Manufacturing NAICS codes
    manufacturing_naics = [
        '31', '32', '33',  # Core manufacturing sectors
        '42',              # Wholesale trade (suppliers)
        '5413', '5416'     # Engineering and technical services
    ]

    # Manufacturing keywords
    manufacturing_keywords = [
        'manufactur', 'supplier', 'raw material', 'components', 'parts', 'machinery',
        'equipment', 'tool', 'fabrication', 'industrial', 'production', 'assembly',
        'factory', 'plant', 'mill', 'processing', 'wholesale', 'distribution'
    ]

    # Check NAICS code
    naics_columns = ['naics_2022_primary_code', 'naics_code', 'primary_naics']
    naics_code = ""

    for column in naics_columns:
        if column in row.index and pd.notna(row[column]):
            naics_code = str(row[column]).strip()
            break

    naics_match = any(naics_code.startswith(code) for code in manufacturing_naics)

    # Check keywords in descriptions
    description_columns = [
        'short_description', 'long_description', 'business_tags',
        'naics_2022_primary_label', 'company_description', 'description'
    ]

    combined_text = ""
    for column in description_columns:
        if column in row.index and pd.notna(row[column]) and isinstance(row[column], str):
            combined_text += row[column].lower() + " "

    keyword_matches = sum(1 for keyword in manufacturing_keywords if keyword in combined_text)

    # Return True if either NAICS matches OR at least 2 keywords match
    return naics_match or keyword_matches >= 2

def calculate_row_score(row):
    """Calculate a score for a row based on secondary criteria"""
    score = 0

    # Phone data (+1 point)
    if has_phone_data(row):
        score += 1

    # Address data (+2 points)
    if has_address_data(row):
        score += 2

    # Manufacturing relevance (+3 points)
    if check_manufacturing_relevance(row):
        score += 3

    return score

def select_best_row_from_group(company_block, website_columns):
    """
    Select the best row from a group of 5 rows based on criteria:
    1. MUST have website data in any website-related field
    2. Among rows with website data, pick the one with highest score
    """
    valid_rows = []

    for idx in range(min(5, len(company_block))):
        row = company_block.iloc[idx]
        has_website, website_col, website_val = has_website_data_simple(row, website_columns)

        if has_website:
            row_score = calculate_row_score(row)
            valid_rows.append((row_score, idx, row, website_col, website_val))

    # If no rows have website data, return None
    if not valid_rows:
        return None

    # Sort by score (descending) and return the best row
    valid_rows.sort(key=lambda x: x[0], reverse=True)
    best_score, row_idx, best_row, website_col, website_val = valid_rows[0]

    # Add metadata about the selection
    best_row = best_row.copy()
    best_row['selection_score'] = best_score
    best_row['source_row_index'] = row_idx + 1  # 1-based index for human readability
    best_row['detected_website_column'] = website_col
    best_row['detected_website_value'] = website_val

    return best_row

def process_companies(input_file, output_file):
    """Main function to process companies with robust website detection"""
    print("Starting Phase 1a: ROBUST Company Selection")
    print("=" * 70)

    # Load the data
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows from input file")

    # Detect website columns
    website_columns = detect_website_fields(df)
    print(f"\nDetected website-related columns: {', '.join(website_columns) if website_columns else 'None'}")

    if not website_columns:
        print("⚠️  No website-related columns detected! Searching for URL patterns in all text fields...")
        # Fallback: search all string columns for URL patterns
        url_pattern = r'https?://|www\.|[a-zA-Z0-9\-]+\.(com|org|net|io|co|edu|gov|biz|info|me|dev|ai|app)'

        # Find columns that might contain URLs
        text_columns = [col for col in df.columns if df[col].dtype == 'object']
        for column in text_columns:
            sample_values = df[column].dropna().head(10).tolist()
            url_count = sum(1 for val in sample_values if isinstance(val, str) and re.search(url_pattern, val, re.IGNORECASE))
            if url_count > 0:
                print(f"  Found potential URLs in column '{column}' ({url_count}/10 sample rows)")
                website_columns.append(column)

    if not website_columns:
        print("❌ No columns with website information found. Cannot proceed with selection.")
        return None

    # Verify structure
    total_rows = len(df)
    print(f"\nTotal data rows: {total_rows}")

    if total_rows % 5 != 0:
        print(f"⚠️  Warning: Row count ({total_rows}) not divisible by 5")
        print(f"   Expected format: multiples of 5 company rows")

    total_companies = total_rows // 5
    print(f"Processing {total_companies} companies (5 rows per company)")

    selected_companies = []
    disqualified_companies = 0
    sample_rejections = []

    # Process companies in blocks of 5 rows
    for i in range(0, total_rows, 5):
        if i + 5 > total_rows:
            print(f"⚠️  Incomplete company block starting at row {i+2}, skipping")
            continue

        # Extract the 5 rows for this company
        company_block = df.iloc[i:i+5]

        # Get company name for reporting
        company_name = "Unknown"
        name_columns = ['company_name', 'input_company_name', 'name', 'business_name']
        for col in name_columns:
            if col in company_block.columns and pd.notna(company_block.iloc[0][col]):
                name_val = str(company_block.iloc[0][col]).strip()
                if name_val != "":
                    company_name = name_val
                    break

        # Select the best row
        best_row = select_best_row_from_group(company_block, website_columns)

        if best_row is not None:
            selected_companies.append(best_row)
            website_info = f"{best_row['detected_website_column']}: {best_row['detected_website_value'][:50]}"
            print(f"✅ SELECTED: {company_name} (Score: {best_row['selection_score']}, {website_info})")
        else:
            disqualified_companies += 1
            if len(sample_rejections) < 10:  # Only collect first 10 rejections for analysis
                sample_rejections.append(company_name)
            print(f"❌ DISQUALIFIED: {company_name} (No website data found)")

    # Create output dataframe
    if selected_companies:
        result_df = pd.DataFrame(selected_companies)

        # Save the result
        result_df.to_csv(output_file, index=False)

        print("\n" + "=" * 70)
        print("PHASE 1a COMPLETE")
        print("=" * 70)
        print(f"Total companies processed: {total_companies}")
        print(f"Companies SELECTED: {len(selected_companies)}")
        print(f"Companies DISQUALIFIED: {disqualified_companies}")
        print(f"Selection rate: {len(selected_companies)/total_companies:.1%}")
        print(f"\nOutput saved to: {output_file}")

        # Show summary statistics
        if not result_df.empty:
            print(f"\nScoring distribution:")
            score_counts = result_df['selection_score'].value_counts().sort_index()
            for score, count in score_counts.items():
                print(f"  • Score {score}: {count} companies")

            # Show sample of rejected companies for debugging
            if sample_rejections:
                print(f"\nSample of rejected companies (first 10):")
                for company in sample_rejections:
                    print(f"  • {company}")

        return result_df
    else:
        print("❌ NO COMPANIES MET THE SELECTION CRITERIA!")
        print("This is unusual - even major companies like Cloudera, Google, Cisco should have been selected.")
        print("Please check if the data contains website information in unexpected formats or columns.")
        return None

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "presales_data_sample.csv"
    OUTPUT_FILE = "phase1_selected_rows.csv"

    # Verify input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found.")
        print("Please ensure the file is in the current directory or provide the correct path.")
    else:
        # Run the processing
        result = process_companies(INPUT_FILE, OUTPUT_FILE)
