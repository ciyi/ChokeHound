"""
BloodHound Choke Points Analyzer

This script analyzes Active Directory data collected by BloodHound CE to identify
choke points - critical privilege edges that connect non-Tier-0 objects to Tier-0 objects.

Usage:
    python ChokeHound.py [--output OUTPUT_FILENAME]
    
Example:
    python ChokeHound.py --output my_choke_points_report.xlsx
"""

import argparse
import os
import sys
from py2neo import Graph
import pandas as pd

# Import configuration and queries
import config
from queries import QUERIES
import risk_config

# Import reporting functions
from report import create_excel_report


def banner():
    font = """
 .d8888b.  888               888               888    888                                 888      
d88P  Y88b 888               888               888    888                                 888      
888    888 888               888               888    888                                 888      
888        88888b.   .d88b.  888  888  .d88b.  8888888888  .d88b.  888  888 88888b.   .d88888      
888        888 "88b d88""88b 888 .88P d8P  Y8b 888    888 d88""88b 888  888 888 "88b d88" 888      
888    888 888  888 888  888 888888K  88888888 888    888 888  888 888  888 888  888 888  888      
Y88b  d88P 888  888 Y88..88P 888 "88b Y8b.     888    888 Y88..88P Y88b 888 888  888 Y88b 888      
 "Y8888P"  888  888  "Y88P"  888  888  "Y8888  888    888  "Y88P"   "Y88888 888  888  "Y88888      
                                                                                                   
    @ciyinet     @gobispo                                              v0.1 RootedCon Edition                                                                                            
    
                                                                                     
    
    """
    print(font)


def simplify_labels(label_array):
    """
    Simplify label arrays by removing 'Base' and 'Tag_Tier_Zero', 
    keeping the most relevant label.
    
    Examples:
        ['Base', 'Container'] -> 'Container'
        ['Base', 'Group'] -> 'Group'
        ['Base', 'ADLocalGroup', 'Group'] -> 'Group'
        ['Base', 'Computer', 'Tag_Tier_Zero'] -> 'Computer'
        ['Base'] -> 'UNKNOWN'
        '[Base]' -> 'UNKNOWN'
    
    Args:
        label_array: List of labels or string representation of list
        
    Returns:
        Simplified label string, or 'UNKNOWN' if only Base remains
    """
    if not label_array:
        return ""
    
    # Handle string representation of list (from Neo4j)
    if isinstance(label_array, str):
        # Check if it's the string "[Base]" or "Base"
        if label_array.strip() in ['[Base]', 'Base', '["Base"]']:
            return "UNKNOWN"
        # Try to evaluate if it's a string representation of a list
        try:
            import ast
            label_array = ast.literal_eval(label_array)
        except (ValueError, SyntaxError):
            return label_array
    
    # Ensure it's a list
    if not isinstance(label_array, list):
        return str(label_array)
    
    # Filter out 'Base' and 'Tag_Tier_Zero'
    filtered_labels = [label for label in label_array 
                      if label not in ['Base', 'Tag_Tier_Zero']]
    
    # If nothing left, return UNKNOWN (only Base/Tag_Tier_Zero were present)
    if not filtered_labels:
        return "UNKNOWN"
    
    # Return the last (most specific) label
    return filtered_labels[-1]


def process_dataframe_labels(df):
    """
    Process SourceType and TargetType columns to simplify labels.
    Converts "[Base]" or "Base" to "UNKNOWN" when no other labels are present.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        Processed DataFrame
    """
    df = df.copy()
    
    # Process SourceType column
    if 'SourceType' in df.columns:
        df['SourceType'] = df['SourceType'].apply(simplify_labels)
        # Handle case where result is "[Base]" string (shouldn't happen after simplify_labels, but just in case)
        df['SourceType'] = df['SourceType'].replace(['[Base]', 'Base'], 'UNKNOWN')
    
    # Process TargetType column
    if 'TargetType' in df.columns:
        df['TargetType'] = df['TargetType'].apply(simplify_labels)
        # Handle case where result is "[Base]" string (shouldn't happen after simplify_labels, but just in case)
        df['TargetType'] = df['TargetType'].replace(['[Base]', 'Base'], 'UNKNOWN')
    
    return df


def calculate_risk_score(row, return_breakdown=False):
    """
    Calculate risk score for a choke point row.
    
    Risk Formula:
        Risk = (SourceObjectWeight * SourceObjectCategory) +
               (RelationshipTypeWeight * RelationshipTypeCategory) +
               (TargetObjectWeight * TargetObjectCategory) +
               (AffectedAttackPathsWeight * AffectedAttackPathsMultiplier)
    
    Args:
        row: pandas Series representing a row from the DataFrame
        return_breakdown: If True, returns a tuple (risk_score, breakdown_dict)
        
    Returns:
        Risk score (float) or tuple (risk_score, breakdown_dict) if return_breakdown=True
    """
    # Get source object risk
    # Use SourceType and SourceObjectID (SID) to identify common default groups
    # SourceObjectID is particularly useful for unknown source objects where we don't know
    # the name or type, as it provides a unique identifier (SID) for the object
    source_type = row.get('SourceType', '')
    source_object_id = row.get('SourceObjectID', '')
    # Handle None or NaN values from pandas
    if pd.isna(source_object_id):
        source_object_id = ''
    source_name = row.get('SourceName', '')  # Kept for logging purposes
    
    # Get source risk using the helper function that checks for common groups by SID
    # Note: Service accounts cannot be differentiated from regular users in Neo4j labels
    # Both appear as "User", so we treat all users the same
    source_risk = risk_config.get_source_object_risk(source_type, source_object_id, source_name)
    
    # Get relationship type risk
    relationship_type = row.get('RelationshipType', '')
    relationship_risk = risk_config.get_relationship_type_risk(relationship_type)
    
    # Get target object risk (simplified label is a string, not a list)
    # NOTE: Common default groups are NOT considered for target objects - only for source objects
    target_type = row.get('TargetType', '')
    if isinstance(target_type, str):
        target_risk = risk_config.TARGET_OBJECT_CATEGORIES.get(
            target_type,
            risk_config.TARGET_OBJECT_CATEGORIES["default"]
        )
    else:
        target_risk = risk_config.get_target_object_risk(target_type)
    
    # Get affected attack paths multiplier
    affected_paths = row.get('AffectedAttackPaths', 0)
    try:
        affected_paths = int(affected_paths) if pd.notna(affected_paths) else 0
    except (ValueError, TypeError):
        affected_paths = 0
    paths_multiplier = risk_config.get_affected_paths_multiplier(affected_paths)
    
    # Calculate weighted risk score
    weights = risk_config.RISK_WEIGHTS
    source_component = weights["source_object"] * source_risk
    relationship_component = weights["relationship_type"] * relationship_risk
    target_component = weights["target_object"] * target_risk
    paths_component = weights["affected_attack_paths"] * paths_multiplier * 10  # Scale multiplier
    
    risk_score = (
        source_component +
        relationship_component +
        target_component +
        paths_component
    )
    
    risk_score = round(risk_score, 2)
    
    if return_breakdown:
        breakdown = {
            'source_name': source_name,
            'source_type': source_type,
            'source_risk_category': source_risk,
            'source_weight': weights["source_object"],
            'source_component': round(source_component, 2),
            'relationship_type': relationship_type,
            'relationship_risk_category': relationship_risk,
            'relationship_weight': weights["relationship_type"],
            'relationship_component': round(relationship_component, 2),
            'target_name': row.get('TargetName', ''),
            'target_type': target_type,
            'target_risk_category': target_risk,
            'target_weight': weights["target_object"],
            'target_component': round(target_component, 2),
            'affected_paths': affected_paths,
            'paths_multiplier': paths_multiplier,
            'paths_weight': weights["affected_attack_paths"],
            'paths_component': round(paths_component, 2),
            'total_risk_score': risk_score
        }
        return risk_score, breakdown
    
    return risk_score


def add_risk_column(df, query_name, enable_logging=False):
    """
    Add risk column to DataFrame if it's the "Critical Choke Points Risk" query.
    
    Args:
        df: pandas DataFrame
        query_name: Name of the query
        enable_logging: If True, returns risk breakdowns for logging
        
    Returns:
        DataFrame with RiskScore column added (normalized 1-100 scale)
        If enable_logging=True and query is "Critical Choke Points Risk", also returns list of breakdowns
    """
    risk_breakdowns = []
    
    if query_name == "Critical Choke Points Risk" and not df.empty:
        # Check if required columns exist
        required_cols = ['SourceType', 'RelationshipType', 'TargetType', 'AffectedAttackPaths']
        if all(col in df.columns for col in required_cols):
            df = df.copy()
            
            if enable_logging:
                # Calculate risk with breakdowns - store them in order
                results_list = []
                for idx in df.index:
                    row = df.loc[idx]
                    risk_score, breakdown = calculate_risk_score(row, return_breakdown=True)
                    results_list.append((risk_score, breakdown))
                
                # Always add normalized risk score (1-100 scale)
                df['RiskScore'] = [risk_config.normalize_risk_score(r[0]) for r in results_list]
                # Store breakdowns in original order (will reorder after sorting)
                risk_breakdowns = [r[1] for r in results_list]
            else:
                # Calculate risk scores
                risk_scores = df.apply(calculate_risk_score, axis=1)
                
                # Always add normalized risk score (1-100 scale)
                df['RiskScore'] = risk_scores.apply(risk_config.normalize_risk_score)
            
            # Create a temporary column to track original order for breakdown mapping
            if enable_logging:
                df['_breakdown_idx'] = range(len(df))
            
            # Sort by RiskScore (normalized) descending, then by AffectedAttackPaths descending
            df = df.sort_values(['RiskScore', 'AffectedAttackPaths'], ascending=[False, False])
            
            # Reorder breakdowns to match sorted dataframe
            if enable_logging and risk_breakdowns:
                # Get sorted breakdown indices
                sorted_indices = df['_breakdown_idx'].tolist()
                # Reorder breakdowns according to sorted order
                risk_breakdowns = [risk_breakdowns[int(idx)] for idx in sorted_indices]
                # Remove temporary column
                df = df.drop(columns=['_breakdown_idx'])
            
            # Reset index after sorting
            df = df.reset_index(drop=True)
            
            # Add unique ID column (numeric identifier starting from 1)
            # This should be added after sorting so IDs reflect the priority order
            df.insert(0, 'ID', range(1, len(df) + 1))
    
    if enable_logging:
        return df, risk_breakdowns
    return df




def main():
    """Main function to execute queries and generate Excel report."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Analyze BloodHound data to find choke points in Active Directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ChokeHound.py
  python ChokeHound.py --output my_report.xlsx
  python ChokeHound.py --output my_report.xlsx --log-risk
  python ChokeHound.py -o report.xlsx --log-risk
        """
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=config.DEFAULT_OUTPUT_FILENAME,
        help=f'Output Excel filename (default: {config.DEFAULT_OUTPUT_FILENAME})'
    )
    parser.add_argument(
        '--log-risk',
        action='store_true',
        default=False,
        help='Generate a detailed log file explaining risk calculations for each choke point (includes raw risk scores)'
    )
    args = parser.parse_args()
    
    output_filename = args.output
    enable_logging = args.log_risk
    
    # Ensure .xlsx extension
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    
    # Connect to Neo4j
    print(f"Connecting to Neo4j at {config.NEO4J_URI}...")
    try:
        graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
        print("[OK] Connected to Neo4j")
    except Exception as e:
        print(f"[ERROR] Error connecting to Neo4j: {e}")
        return
    
    # Query domains from Neo4j
    print("Querying Active Directory domains...")
    domains = []
    try:
        domain_query = "MATCH (d:Domain) RETURN d.name"
        domain_results = graph.run(domain_query).data()
        domains = sorted([result['d.name'] for result in domain_results if result.get('d.name')])
        if domains:
            print(f"  [OK] Found {len(domains)} domain(s): {', '.join(domains)}")
        else:
            print("  [WARNING] No domains found in database")
    except Exception as e:
        print(f"  [WARNING] Error querying domains: {e}")
    
    # Store dataframes for post-processing
    dataframes = {}
    risk_breakdowns = []
    
    # Execute queries and collect results
    for sheet_name, cypher in QUERIES.items():
        print(f"Running query: {sheet_name}")
        try:
            df = graph.run(cypher).to_data_frame()
            if df.empty:
                df = pd.DataFrame([{"Info": "No results found"}])
            else:
                # Process labels
                df = process_dataframe_labels(df)
                # Add risk column for "Critical Choke Points Risk" query
                if enable_logging and sheet_name == "Critical Choke Points Risk":
                    df, breakdowns = add_risk_column(df, sheet_name, enable_logging=True)
                    risk_breakdowns = breakdowns
                else:
                    df = add_risk_column(df, sheet_name, enable_logging=False)
            
            # Store dataframe with original sheet name (will be truncated in report.py)
            dataframes[sheet_name] = df
            print(f"  [OK] {len(df)} rows returned")
        except Exception as e:
            print(f"  [WARNING] Error running '{sheet_name}': {e}")
            # Create error sheet
            error_df = pd.DataFrame([{"Error": str(e)}])
            dataframes[sheet_name] = error_df
    
    # Generate Excel report
    create_excel_report(dataframes, output_filename, risk_breakdowns, enable_logging, domains)


if __name__ == "__main__":
    banner()
    main()

