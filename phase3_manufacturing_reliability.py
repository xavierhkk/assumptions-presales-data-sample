import pandas as pd
import numpy as np
import os
import re
from datetime import datetime

def detect_capability_columns(df):
    """Dynamically detect columns that contain capability information"""
    employee_columns = []
    revenue_columns = []
    year_columns = []
    location_columns = []
    country_columns = []

    for column in df.columns:
        col_lower = column.lower()

        # Employee-related columns
        if any(term in col_lower for term in ['employee', 'staff', 'workforce', 'headcount']):
            employee_columns.append(column)

        # Revenue-related columns
        if any(term in col_lower for term in ['revenue', 'turnover', 'sales', 'income', 'financial']):
            revenue_columns.append(column)

        # Year founded columns
        if any(term in col_lower for term in ['year', 'founded', 'established', 'created']):
            year_columns.append(column)

        # Location-related columns
        if any(term in col_lower for term in ['location', 'branch', 'office', 'facility', 'site']):
            location_columns.append(column)

        # Country columns
        if any(term in col_lower for term in ['country', 'nation', 'region', 'headquarters']):
            country_columns.append(column)

    return {
        'employee': employee_columns,
        'revenue': revenue_columns,
        'year': year_columns,
        'location': location_columns,
        'country': country_columns
    }

def parse_numeric_value(value):
    """Parse various numeric formats including currency and formatted numbers"""
    if pd.isna(value) or not isinstance(value, str):
        return None

    value = value.strip().lower()

    # Handle "not available" type values
    if value in ["not available", "n/a", "none", "not applicable", "no data", "unknown", ""]:
        return None

    # Handle currency formats like "$10M", "€5.5M", "10 million"
    if 'million' in value or 'm' in value or 'mn' in value:
        # Extract numeric part
        num_match = re.search(r'[\d,.]+', value)
        if num_match:
            num_str = num_match.group().replace(',', '')
            try:
                return float(num_str) * 1_000_000
            except:
                return None

    if 'billion' in value or 'b' in value:
        num_match = re.search(r'[\d,.]+', value)
        if num_match:
            num_str = num_match.group().replace(',', '')
            try:
                return float(num_str) * 1_000_000_000
            except:
                return None

    # Handle simple numeric values
    try:
        # Remove currency symbols and commas
        clean_value = re.sub(r'[^\d.-]', '', value)
        if clean_value:
            return float(clean_value)
    except:
        pass

    return None

def assess_company_size_flexible(row, employee_columns):
    """More flexible employee count assessment"""
    # First, try to find actual employee count
    for col in employee_columns:
        if col in row.index and pd.notna(row[col]):
            value = parse_numeric_value(str(row[col]))
            if value is not None:
                if value >= 500:
                    return 5, f"{value:,.0f} employees (Large)"
                elif value >= 100:
                    return 4, f"{value:,.0f} employees (Medium-Large)"
                elif value >= 50:
                    return 3, f"{value:,.0f} employees (Medium)"
                elif value >= 10:
                    return 2, f"{value:,.0f} employees (Small)"
                else:
                    return 1, f"{value:,.0f} employees (Micro)"

    # If no numeric value found, look for employee count type descriptions
    for col in employee_columns:
        if col in row.index and pd.notna(row[col]):
            value_str = str(row[col]).lower()
            if any(term in value_str for term in ['large', 'enterprise', '500+', '1000+']):
                return 4, "Large company (based on description)"
            elif any(term in value_str for term in ['medium', '100-500', '50-250']):
                return 3, "Medium company (based on description)"
            elif any(term in value_str for term in ['small', '10-50', '1-50']):
                return 2, "Small company (based on description)"

    # Default fallback - assume some size if company exists
    return 2, "Small company (default assumption)"

def assess_company_stability_flexible(row, year_columns):
    """More flexible stability assessment"""
    current_year = datetime.now().year

    for col in year_columns:
        if col in row.index and pd.notna(row[col]):
            try:
                # Try to parse year directly
                year_val = int(str(row[col]).strip())
                if 1900 <= year_val <= current_year:
                    years_in_business = current_year - year_val
                    if years_in_business >= 20:
                        return 5, f"Founded {year_val} ({years_in_business} years)"
                    elif years_in_business >= 10:
                        return 4, f"Founded {year_val} ({years_in_business} years)"
                    elif years_in_business >= 5:
                        return 3, f"Founded {year_val} ({years_in_business} years)"
                    elif years_in_business >= 2:
                        return 2, f"Founded {year_val} ({years_in_business} years)"
                    else:
                        return 1, f"Founded {year_val} ({years_in_business} years)"
            except:
                # Try to extract year from text
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', str(row[col]))
                if year_match:
                    year_val = int(year_match.group())
                    if 1900 <= year_val <= current_year:
                        years_in_business = current_year - year_val
                        if years_in_business >= 20:
                            return 5, f"Founded {year_val} ({years_in_business} years)"
                        elif years_in_business >= 10:
                            return 4, f"Founded {year_val} ({years_in_business} years)"
                        elif years_in_business >= 5:
                            return 3, f"Founded {year_val} ({years_in_business} years)"
                        elif years_in_business >= 2:
                            return 2, f"Founded {year_val} ({years_in_business} years)"
                        else:
                            return 1, f"Founded {year_val} ({years_in_business} years)"

    # Default fallback
    return 3, "Established company (default assumption)"

def assess_financial_strength_flexible(row, revenue_columns):
    """More flexible financial strength assessment"""
    for col in revenue_columns:
        if col in row.index and pd.notna(row[col]):
            value = parse_numeric_value(str(row[col]))
            if value is not None:
                if value >= 50_000_000:  # $50M+
                    return 5, f"${value/1_000_000:,.1f}M revenue (Large)"
                elif value >= 10_000_000:  # $10M+
                    return 4, f"${value/1_000_000:,.1f}M revenue (Medium-Large)"
                elif value >= 1_000_000:  # $1M+
                    return 3, f"${value/1_000_000:,.1f}M revenue (Medium)"
                elif value >= 100_000:  # $100K+
                    return 2, f"${value/1_000:,.0f}K revenue (Small)"
                else:
                    return 1, f"${value:,.0f} revenue (Micro)"

    # Default fallback
    return 2, "Small revenue (default assumption)"

def assess_geographical_presence_flexible(row, location_columns, country_columns):
    """More flexible geographical presence assessment"""
    # First try to get number of locations
    location_count = None
    for col in location_columns:
        if col in row.index and pd.notna(row[col]):
            try:
                location_count = int(str(row[col]).strip())
                break
            except:
                pass

    # Get countries
    countries = []
    for col in country_columns:
        if col in row.index and pd.notna(row[col]):
            country_val = str(row[col]).strip()
            if country_val and country_val.lower() not in ["not available", "n/a", "none"]:
                # Split if multiple countries
                if ',' in country_val or ';' in country_val or '|' in country_val:
                    countries = [c.strip() for c in re.split(r'[;,|]', country_val) if c.strip()]
                else:
                    countries = [country_val]
                break

    # Score based on what we found
    if location_count is not None and location_count >= 5:
        return 5, f"{location_count} locations across {len(countries)} countries"
    elif location_count is not None and location_count >= 3:
        return 4, f"{location_count} locations across {len(countries)} countries"
    elif location_count is not None and location_count >= 2:
        return 3, f"{location_count} locations across {len(countries)} countries"
    elif countries:
        if len(countries) >= 3:
            return 4, f"Present in {len(countries)} countries: {', '.join(countries[:3])}"
        elif len(countries) >= 2:
            return 3, f"Present in {len(countries)} countries: {', '.join(countries)}"
        else:
            return 2, f"Present in {countries[0]}"
    else:
        # Default fallback
        return 2, "Single location (default assumption)"

def calculate_capability_score_flexible(row, capability_columns):
    """Calculate capability score with more flexible logic"""
    # Get scores from each dimension
    size_score, size_info = assess_company_size_flexible(row, capability_columns['employee'])
    stability_score, stability_info = assess_company_stability_flexible(row, capability_columns['year'])
    financial_score, financial_info = assess_financial_strength_flexible(row, capability_columns['revenue'])
    geo_score, geo_info = assess_geographical_presence_flexible(row, capability_columns['location'], capability_columns['country'])

    # Weighted scoring
    capability_score = (size_score * 0.3 + stability_score * 0.3 + financial_score * 0.4)
    total_score = (capability_score * 0.7 + geo_score * 0.3)

    score_breakdown = {
        'company_size': size_score,
        'company_stability': stability_score,
        'financial_strength': financial_score,
        'geographical_presence': geo_score,
        'capability_score': round(capability_score, 1),
        'total_score': round(total_score, 1)
    }

    return total_score, score_breakdown, {
        'size_info': size_info,
        'stability_info': stability_info,
        'financial_info': financial_info,
        'geo_info': geo_info
    }

def is_suitable_supplier_flexible(score_breakdown, min_capability_score=1.5, min_geo_score=1.0):
    """More flexible supplier qualification criteria"""
    capability_score = score_breakdown['capability_score']
    geo_score = score_breakdown['geographical_presence']

    # Much more lenient thresholds
    if capability_score >= min_capability_score and geo_score >= min_geo_score:
        return True
    return False

def filter_suppliers_flexible(input_file, output_file, rejected_file=None):
    """Main function with flexible scoring and detection"""
    print("Starting Phase 3: FLEXIBLE Supplier Capability & Geographical Analysis")
    print("=" * 70)

    # Load the Phase 2 results
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} manufacturing companies from Phase 2 output")
    print(f"Available columns: {', '.join(df.columns.tolist())}")

    # Detect capability columns
    capability_columns = detect_capability_columns(df)
    print(f"\nDetected capability columns:")
    for category, columns in capability_columns.items():
        print(f"  {category}: {', '.join(columns) if columns else 'None'}")

    # Show sample data for debugging
    print(f"\nSample data from first row:")
    sample_row = df.iloc[0]
    for category, columns in capability_columns.items():
        for col in columns:
            if col in sample_row.index:
                print(f"  {col}: {sample_row[col]}")

    # Prepare for filtering
    suitable_suppliers = []
    rejected_suppliers = []
    score_distribution = {}

    print(f"\nAssessing supplier capability with FLEXIBLE criteria...")
    print("-" * 70)

    # Process each company
    for idx, row in df.iterrows():
        # Get company name for reporting
        company_name = "Unknown"
        for field in ['company_name', 'input_company_name', 'business_name']:
            if field in row.index and pd.notna(row[field]) and str(row[field]).strip() != "":
                company_name = str(row[field]).strip()
                break

        # Calculate scores
        total_score, score_breakdown, info_details = calculate_capability_score_flexible(row, capability_columns)

        # Track score distribution
        cap_score = score_breakdown['capability_score']
        geo_score = score_breakdown['geographical_presence']
        score_key = f"{cap_score:.1f}/{geo_score:.1f}"
        score_distribution[score_key] = score_distribution.get(score_key, 0) + 1

        # Determine if suitable supplier
        is_suitable = is_suitable_supplier_flexible(score_breakdown)

        if is_suitable:
            row_copy = row.copy()
            row_copy['total_supplier_score'] = total_score
            row_copy['capability_score'] = cap_score
            row_copy['geographical_score'] = geo_score
            row_copy['company_size_info'] = info_details['size_info']
            row_copy['stability_info'] = info_details['stability_info']
            row_copy['financial_info'] = info_details['financial_info']
            row_copy['geographical_info'] = info_details['geo_info']
            row_copy['score_breakdown'] = str(score_breakdown)
            suitable_suppliers.append(row_copy)
            print(f"✅ QUALIFIED: {company_name} (Cap: {cap_score:.1f}/5.0, Geo: {geo_score:.1f}/5.0)")
        else:
            rejection_reasons = []
            if cap_score < 1.5:
                rejection_reasons.append(f"Low capability ({cap_score:.1f}/5.0)")
            if geo_score < 1.0:
                rejection_reasons.append(f"Poor geography ({geo_score:.1f}/5.0)")

            rejected_suppliers.append({
                'company_name': company_name,
                'capability_score': cap_score,
                'geographical_score': geo_score,
                'rejection_reasons': '; '.join(rejection_reasons) if rejection_reasons else 'Failed flexible criteria',
                'company_size': info_details['size_info'],
                'stability': info_details['stability_info'],
                'financial_strength': info_details['financial_info'],
                'geographical_presence': info_details['geo_info']
            })
            print(f"❌ REJECTED: {company_name} ({'; '.join(rejection_reasons)})")

    # Create output dataframe
    print("\n" + "=" * 70)
    print("PHASE 3 FLEXIBLE ANALYSIS COMPLETE")
    print("=" * 70)

    if suitable_suppliers:
        result_df = pd.DataFrame(suitable_suppliers)

        # Save the result
        result_df.to_csv(output_file, index=False)

        print(f"Qualified suppliers: {len(suitable_suppliers)}")
        print(f"Rejected suppliers: {len(rejected_suppliers)}")
        print(f"Qualification rate: {len(suitable_suppliers)/len(df):.1%}")
        print(f"Output saved to: {output_file}")

        # Show score distribution
        print(f"\nScore distribution summary (top 10):")
        sorted_distribution = sorted(score_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        for score_range, count in sorted_distribution:
            print(f"  • {score_range}: {count} companies")

        # Show top suppliers
        if not result_df.empty:
            print(f"\nTop 10 suppliers by total score:")
            top_suppliers = result_df.sort_values('total_supplier_score', ascending=False).head(10)
            for i, (_, row) in enumerate(top_suppliers.iterrows(), 1):
                print(f"  {i}. {row['company_name']}: {row['total_supplier_score']:.1f}/5.0 (Size: {row['company_size_info']})")

        return result_df
    else:
        print("❌ WARNING: NO COMPANIES QUALIFIED with flexible criteria!")
        print("This suggests the data may not contain sufficient capability information.")
        print("Consider checking the input file structure or lowering criteria further.")

        # Show why companies were rejected
        if rejected_suppliers:
            print(f"\nSample rejection reasons (first 10):")
            for i, supplier in enumerate(rejected_suppliers[:10], 1):
                print(f"  {i}. {supplier['company_name']}: {supplier['rejection_reasons']}")

        return None

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "phase2_manufacturing_companies.csv"  # Output from Phase 2
    OUTPUT_FILE = "phase3_qualified_suppliers.csv"
    REJECTED_FILE = "phase3_rejected_suppliers.csv"

    # Verify input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found.")
        print("Please ensure Phase 2 has been run successfully and the output file exists.")
    else:
        # Run the filtering
        result = filter_suppliers_flexible(INPUT_FILE, OUTPUT_FILE, REJECTED_FILE)
