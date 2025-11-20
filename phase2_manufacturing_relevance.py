import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

def detect_manufacturing_columns(df):
    """Detect columns that might contain manufacturing relevance information"""
    description_columns = []
    naics_columns = []
    tag_columns = []

    for column in df.columns:
        column_lower = column.lower()

        # NAICS code columns
        if any(pattern in column_lower for pattern in ['naics', 'sic', 'industry_code', 'sector_code']):
            naics_columns.append(column)

        # Description columns
        if any(pattern in column_lower for pattern in ['desc', 'about', 'profile', 'overview', 'summary']):
            description_columns.append(column)

        # Tag columns
        if any(pattern in column_lower for pattern in ['tag', 'keyword', 'category', 'sector', 'industry']):
            tag_columns.append(column)

    return naics_columns, description_columns, tag_columns

def get_manufacturing_naics_codes():
    """Return comprehensive list of manufacturing-relevant NAICS codes"""
    return [
        # Core manufacturing sectors
        '31', '32', '33',  # Manufacturing sector
        '311', '312', '313', '314', '315', '316',  # Food, textile, apparel manufacturing
        '321', '322', '323', '324', '325', '326', '327', '331', '332', '333', '334', '335', '336', '337', '339',  # Detailed manufacturing

        # Supplier and distribution sectors
        '42',  # Wholesale Trade
        '421', '422', '423', '424', '425',  # Wholesale trade subsectors

        # Engineering and technical services
        '5413',  # Architectural, engineering, and related services
        '54133',  # Engineering services
        '54134',  # Drafting services
        '54138',  # Testing laboratories
        '54169',  # Other scientific and technical consulting services

        # Repair and maintenance
        '811',  # Repair and maintenance
        '8113',  # Commercial and industrial machinery and equipment repair and maintenance

        # Construction-related manufacturing
        '238',  # Specialty trade contractors (often work with manufactured products)

        # Professional services supporting manufacturing
        '5414',  # Specialized design services
        '5415',  # Computer systems design and related services
        '5419',  # Other professional, scientific, and technical services
    ]

def get_manufacturing_keywords():
    """Return comprehensive list of manufacturing-relevant keywords"""
    return [
        # Core manufacturing terms
        'manufactur', 'fabrication', 'production', 'assembly', 'processing',
        'factory', 'plant', 'mill', 'workshop', 'facility', 'facility',

        # Product types
        'components', 'parts', 'raw material', 'materials', 'supplies',
        'goods', 'products', 'equipment', 'machinery', 'tools', 'hardware',
        'instrument', 'device', 'apparatus', 'machine', 'system',

        # Industry sectors
        'industrial', 'mechanical', 'electrical', 'electronics', 'electronic',
        'chemical', 'pharmaceutical', 'biotech', 'aerospace', 'automotive',
        'automobile', 'vehicle', 'metal', 'steel', 'aluminum', 'plastic', 'polymer',
        'composite', 'textile', 'garment', 'apparel', 'food', 'beverage', 'pharma',

        # Supplier relationships
        'supplier', 'vendor', 'distributor', 'wholesale', 'wholesaler',
        'provider', 'source', 'procurement', 'sourcing', 'b2b', 'business-to-business',
        'supply chain', 'logistics', 'warehousing', 'inventory',

        # Manufacturing processes
        'casting', 'molding', 'forging', 'stamping', 'welding', 'machining',
        'cnc', 'cutting', 'forming', 'shaping', 'finishing', 'coating', 'plating',
        'heat treatment', 'testing', 'quality control', 'inspection', 'calibration',

        # Business descriptions
        'oem', 'original equipment manufacturer', 'contract manufacturing',
        'custom manufacturing', 'precision manufacturing', 'industrial supplies',
        'industrial equipment', 'machine parts', 'industrial automation'
    ]

def check_naics_manufacturing_relevance(row, naics_columns, manufacturing_naics):
    """Check if any NAICS code in the row indicates manufacturing relevance"""
    for column in naics_columns:
        if column in row.index and pd.notna(row[column]):
            naics_value = str(row[column]).strip()
            if naics_value != "":
                # Check if the NAICS code starts with any manufacturing prefix
                for code in manufacturing_naics:
                    if naics_value.startswith(code):
                        return True, code, naics_value

    return False, None, None

def check_keyword_manufacturing_relevance(row, description_columns, tag_columns, manufacturing_keywords):
    """Check if descriptions or tags contain manufacturing keywords"""
    combined_text = ""

    # Combine all description fields
    for column in description_columns:
        if column in row.index and pd.notna(row[column]) and isinstance(row[column], str):
            combined_text += row[column].lower() + " "

    # Combine all tag fields
    for column in tag_columns:
        if column in row.index and pd.notna(row[column]) and isinstance(row[column], str):
            combined_text += row[column].lower() + " "

    # Count keyword matches
    found_keywords = []
    for keyword in manufacturing_keywords:
        if keyword in combined_text and keyword not in found_keywords:
            found_keywords.append(keyword)

    # Require at least 2 distinct manufacturing keywords
    if len(found_keywords) >= 2:
        return True, found_keywords

    return False, found_keywords

def calculate_manufacturing_score(row, naics_columns, description_columns, tag_columns, manufacturing_naics, manufacturing_keywords):
    """Calculate a comprehensive manufacturing relevance score"""
    score = 0
    evidence = []

    # Check NAICS codes (+3 points if match)
    naics_match, matched_code, naics_value = check_naics_manufacturing_relevance(row, naics_columns, manufacturing_naics)
    if naics_match:
        score += 3
        evidence.append(f"NAICS match: {matched_code} ({naics_value})")

    # Check keywords (+2 points if at least 2 keywords found)
    keyword_match, found_keywords = check_keyword_manufacturing_relevance(row, description_columns, tag_columns, manufacturing_keywords)
    if keyword_match:
        score += 2
        evidence.append(f"Keywords match: {', '.join(found_keywords[:3])}")

    # Check company name for manufacturing terms (+1 point)
    company_name_fields = ['company_name', 'business_name', 'name', 'input_company_name']
    company_name = ""
    for field in company_name_fields:
        if field in row.index and pd.notna(row[field]) and isinstance(row[field], str):
            company_name = row[field].lower()
            break

    if company_name:
        name_keywords = [kw for kw in manufacturing_keywords if kw in company_name]
        if name_keywords:
            score += 1
            evidence.append(f"Name contains: {', '.join(name_keywords[:2])}")

    return score, evidence

def is_strictly_manufacturing_relevant(score):
    """Determine if a company is strictly manufacturing-relevant based on score"""
    # Strict criteria: must have either NAICS match OR at least 2 keywords
    # Score threshold: 2+ points required for manufacturing relevance
    return score >= 2

def filter_manufacturing_companies(input_file, output_file):
    """Main function to filter companies for manufacturing relevance"""
    print("Starting Phase 2: STRICT Manufacturing Relevance Filtering")
    print("=" * 70)

    # Load the Phase 1a results
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} companies from Phase 1a output")

    # Get manufacturing criteria
    manufacturing_naics = get_manufacturing_naics_codes()
    manufacturing_keywords = get_manufacturing_keywords()

    # Detect relevant columns
    naics_columns, description_columns, tag_columns = detect_manufacturing_columns(df)

    print(f"\nDetected columns:")
    print(f"NAICS columns: {', '.join(naics_columns) if naics_columns else 'None'}")
    print(f"Description columns: {', '.join(description_columns) if description_columns else 'None'}")
    print(f"Tag columns: {', '.join(tag_columns) if tag_columns else 'None'}")

    # Prepare for filtering
    manufacturing_companies = []
    non_manufacturing_companies = []
    score_distribution = {}

    print(f"\nProcessing {len(df)} companies for manufacturing relevance...")
    print("-" * 70)

    # Process each company
    for idx, row in df.iterrows():
        # Get company name for reporting
        company_name = "Unknown"
        for field in ['company_name', 'input_company_name', 'business_name']:
            if field in row.index and pd.notna(row[field]) and str(row[field]).strip() != "":
                company_name = str(row[field]).strip()
                break

        # Calculate manufacturing score
        score, evidence = calculate_manufacturing_score(
            row, naics_columns, description_columns, tag_columns,
            manufacturing_naics, manufacturing_keywords
        )

        # Track score distribution
        score_distribution[score] = score_distribution.get(score, 0) + 1

        # Determine if manufacturing relevant
        is_manufacturing = is_strictly_manufacturing_relevant(score)

        if is_manufacturing:
            row_copy = row.copy()
            row_copy['manufacturing_score'] = score
            row_copy['manufacturing_evidence'] = '; '.join(evidence) if evidence else 'Score threshold met'
            manufacturing_companies.append(row_copy)
            print(f"✅ MANUFACTURING: {company_name} (Score: {score}/6)")
        else:
            non_manufacturing_companies.append({
                'company_name': company_name,
                'manufacturing_score': score,
                'reason': 'Insufficient manufacturing relevance evidence' if score < 2 else 'Failed strict criteria',
                'naics_codes': ', '.join([str(row[col]) for col in naics_columns if col in row.index and pd.notna(row[col])][:2]),
                'evidence': '; '.join(evidence) if evidence else 'No relevant evidence found'
            })
            print(f"❌ NON-MANUFACTURING: {company_name} (Score: {score}/6)")

    # Create output dataframe
    if manufacturing_companies:
        result_df = pd.DataFrame(manufacturing_companies)

        # Save the result
        result_df.to_csv(output_file, index=False)

        print("\n" + "=" * 70)
        print("PHASE 2 COMPLETE")
        print("=" * 70)
        print(f"Total companies processed: {len(df)}")
        print(f"Manufacturing companies SELECTED: {len(manufacturing_companies)}")
        print(f"Non-manufacturing companies FILTERED OUT: {len(non_manufacturing_companies)}")
        print(f"Retention rate: {len(manufacturing_companies)/len(df):.1%}")
        print(f"\nOutput saved to: {output_file}")

        # Show score distribution
        print(f"\nManufacturing score distribution:")
        for score in sorted(score_distribution.keys()):
            print(f"  • Score {score}: {score_distribution[score]} companies")

        # Show top manufacturing sectors
        if naics_columns and manufacturing_companies:
            print(f"\nTop NAICS codes among manufacturing companies:")
            naics_col = naics_columns[0]
            if naics_col in result_df.columns:
                naics_counts = result_df[naics_col].value_counts().head(10)
                for code, count in naics_counts.items():
                    print(f"  • {code}: {count} companies")

        # Save non-manufacturing companies for analysis
        non_manufacturing_file = output_file.replace('.csv', '_non_manufacturing.csv')
        pd.DataFrame(non_manufacturing_companies).to_csv(non_manufacturing_file, index=False)
        print(f"\nNon-manufacturing companies saved to: {non_manufacturing_file}")

        return result_df
    else:
        print("❌ NO COMPANIES MET THE STRICT MANUFACTURING CRITERIA!")
        print("This indicates the filtering criteria may be too strict or data may lack manufacturing relevance indicators.")
        return None

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "phase1_pragmatic_selected_rows.csv"  # Output from Phase 1
    OUTPUT_FILE = "phase2_manufacturing_companies.csv"

    # Verify input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found.")
        print("Please ensure Phase 1a has been run successfully and the output file exists.")
    else:
        # Run the filtering
        result = filter_manufacturing_companies(INPUT_FILE, OUTPUT_FILE)
