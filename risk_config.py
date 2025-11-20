"""
Risk calculation configuration for choke points.
This file defines weights and categories used to calculate risk scores.

Risk Formula (to be implemented):
    Risk = (SourceObjectWeight * SourceObjectCategory) +
           (RelationshipTypeWeight * RelationshipTypeCategory) +
           (TargetObjectWeight * TargetObjectCategory) +
           (AffectedAttackPathsWeight * AffectedAttackPathsMultiplier)

Where:
    - SourceObjectCategory: Risk category based on source object type
    - RelationshipTypeCategory: Risk category based on relationship type
    - TargetObjectCategory: Risk category based on target object type
    - AffectedAttackPathsMultiplier: Scaling factor based on number of affected paths
"""

# Weights for each component in the risk calculation
# Adjust these values to prioritize different aspects of the risk
RISK_WEIGHTS = {
    "source_object": 0.25,      # Weight for source object type
    "relationship_type": 0.35,  # Weight for relationship type (typically most important)
    "target_object": 0.20,      # Weight for target object type
    "affected_attack_paths": 0.20  # Weight for number of affected attack paths
}

# Note: Min/max risk scores are calculated dynamically based on current configuration
# See calculate_risk_score_range() function below

# Common/default groups identified by SID (Security Identifier)
# These groups have HIGHER risk since any privilege granted to them affects ALL domain users/computers
# NOTE: This list is ONLY used for SOURCE objects, NOT for target objects.
# Target objects use standard risk categories regardless of group SID.

# Well-known SIDs (match by suffix pattern - domain prefix may vary)
# Format: DOMAINNAME-S-1-X-Y or ends with -S-1-X-Y
COMMON_DEFAULT_GROUP_SID_PATTERNS = {
    "Everyone": "-S-1-1-0",                    # Ends with -S-1-1-0
    "Authenticated Users": "-S-1-5-11",        # Ends with -S-1-5-11
    "Pre-Windows 2000 Compatible Access": "-S-1-5-32-554",  # Ends with -S-1-5-32-554
    "Users": "-S-1-5-32-545",                  # Ends with -S-1-5-32-545
    "Guests": "-S-1-5-32-546"                  # Ends with -S-1-5-32-546
}

# Domain-specific SIDs (match by RID - Relative Identifier, the last part after the domain SID)
# Format: S-1-5-21-<domainSID>-<RID>
COMMON_DEFAULT_GROUP_RIDS = {
    "Domain Users": "513",      # RID 513
    "Domain Computers": "515",  # RID 515
    "Domain Guests": "514"      # RID 514
}

# Risk categories for Source Object types
# Higher values indicate higher risk
# Note: Domain objects should not appear as sources in choke points (they are Tier-0)
SOURCE_OBJECT_CATEGORIES = {
    # User accounts
    "User": 3,
    "Computer": 2,
    
    # Groups
    "Group": 4,  # Groups can contain many users (default risk)
    "LocalGroup": 3,
    "Group_CommonDefault": 6,  # Common default groups (Everyone, Domain Users, etc.) - HIGH risk since affects all users
    
    # Containers and OUs
    "OU": 2,
    "Container": 1,
    "GPO": 3,
    
    # Default/unknown
    "default": 2
}

# Risk categories for Relationship Types
# Higher values indicate higher risk (more dangerous privileges)
RELATIONSHIP_TYPE_CATEGORIES = {
    # Critical privileges
    "Owns": 10,
    "DCSync": 10,
    "GoldenCert": 10,
    "GenericAll": 9,
    "WriteOwner": 9,
    "WriteDacl": 9,
    "AllExtendedRights": 9,
    "ForceChangePassword": 8,
    "AddMember": 8,
    
    # High-risk privileges
    "AdminTo": 8,
    "CanPSRemote": 7,
    "ExecuteDCOM": 7,
    "SQLAdmin": 8,
    "DumpSMSAPassword": 9,
    "ReadLAPSPassword": 8,
    "ReadGMSAPassword": 8,
    "SyncLAPSPassword": 8,
    "AddKeyCredentialLink": 9,

    
    # ADCS escalation paths
    "ADCSESC1": 9,
    "ADCSESC3": 9,
    "ADCSESC4": 9,
    "ADCSESC6a": 9,
    "ADCSESC6b": 9,
    "ADCSESC9a": 9,
    "ADCSESC9b": 9,
    "ADCSESC10a": 9,
    "ADCSESC10b": 9,
    "ADCSESC13": 9,
    "ManageCA": 9,
    "ManageCertificates": 9,
    
    # Medium-risk privileges
    "GenericWrite": 6,
    "WriteSPN": 6,
    "CanRDP": 6,
    "WriteAccountRestrictions": 5,
    "WriteGPLink": 5,
    "AddSelf": 7,
    "MemberOf": 4,
    
    # Delegation and trust
    "AllowedToDelegate": 7,
    "AllowedToAct": 6,
    "AddAllowedToAct": 6,
    "HasTrustKeys": 8,
    "DCFor": 8,
    "SameForestTrust": 7,
    
    # Session and authentication
    "HasSession": 4,
    "CoerceToTGT": 7,
    "HasSIDHistory": 4,
    "SpoofSIDHistory": 7,
    "AbuseTGTDelegation": 7,
    
    # GPO and policy
    "GPLink": 4,
    "GPOAppliesTo": 4,
    "CanApplyGPO": 4,
    
    # NTLM relay attacks
    "CoerceAndRelayNTLMToSMB": 5,
    "CoerceAndRelayNTLMToADCS": 6,
    "CoerceAndRelayNTLMToLDAP": 5,
    "CoerceAndRelayNTLMToLDAPS": 5,
    
    # Limited rights
    "WriteOwnerLimitedRights": 5,
    "OwnsLimitedRights": 5,
    
    # Other
    "ClaimSpecialIdentity": 5,
    "ContainsIdentity": 4,
    "PropagatesACEsTo": 5,
    "Contains": 3,
    "SyncedToEntraUser": 4,
    
    # Default for unknown relationship types
    "default": 3
}

# Risk categories for Target Object types
# Higher values indicate higher risk (more critical targets)
TARGET_OBJECT_CATEGORIES = {
    # Domain controllers and critical infrastructure
    "Domain": 10,
    "Computer": 7,  # Especially if it's a DC
    "GPO": 6,
    
    "User": 8,  # Especially admin accounts
    
    # Groups
    "Group": 8,  # Especially admin groups
    "LocalGroup": 6,
    
    # Containers
    "OU": 5,
    "Container": 4,
    
    # Default
    "default": 5
}

# Multiplier for Affected Attack Paths
# This defines how the number of affected paths scales the risk
# Format: (min_paths, max_paths, multiplier)
# For paths >= min_paths and < max_paths, use the multiplier
# Note: There will never be 0 paths (it wouldn't be a choke point)
AFFECTED_ATTACK_PATHS_MULTIPLIERS = [
    (1, 2, 1.0),        # 1 path: no multiplier (1.0x)
    (2, 10, 1.2),       # 2-9 paths: 1.2x
    (10, 50, 1.5),      # 10-49 paths: 1.5x
    (50, 100, 2.0),     # 50-99 paths: 2.0x
    (100, 500, 2.5),    # 100-499 paths: 2.5x
    (500, float('inf'), 3.0)  # 500+ paths: 3.0x
]


def get_source_object_risk(source_type, source_object_id=None, source_name=None):
    """
    Get risk category for source object based on its type and SID (Security Identifier).
    
    NOTE: Common default groups (Everyone, Domain Users, etc.) are only checked for SOURCE objects.
    Target objects do NOT use common default group logic - they use standard risk categories.
    
    Args:
        source_type: String type of the source object (e.g., "Group", "User", "Computer")
        source_object_id: Optional SID (Security Identifier) of the source object
                         Used to identify common default groups by SID pattern or RID
        source_name: Optional name of the source object (kept for backward compatibility, not used for group identification)
        
    Returns:
        Risk category value (int)
    """
    if not source_type:
        return SOURCE_OBJECT_CATEGORIES["default"]
    
    # Check if it's a common default group (HIGH RISK - affects all domain users)
    # NOTE: This check is ONLY for source objects, NOT targets
    if source_type == "Group" and source_object_id:
        # Convert to string and handle None/empty values
        sid = str(source_object_id).strip() if source_object_id else ""
        
        if sid:
            sid = sid.upper()  # Normalize to uppercase for comparison
            
            # Check well-known SID patterns (domain prefix may vary)
            # These SIDs end with specific patterns like -S-1-1-0, -S-1-5-11, etc.
            # Examples: "DOMAINNAME.LOCAL-S-1-1-0", "DOMAINNAME-S-1-5-11"
            for group_name, pattern in COMMON_DEFAULT_GROUP_SID_PATTERNS.items():
                pattern_upper = pattern.upper()
                if sid.endswith(pattern_upper):
                    return SOURCE_OBJECT_CATEGORIES["Group_CommonDefault"]
            
            # Check domain-specific SIDs by RID (Relative Identifier)
            # Format: S-1-5-21-<domainSID>-<RID>
            # Examples: "S-1-5-21-11398407-1185650032-2266222536-513"
            # Extract the RID (last part after the last dash)
            if sid.startswith("S-1-5-21-"):
                # Split by dash and get the last part (RID)
                sid_parts = sid.split("-")
                if len(sid_parts) >= 4:  # At least S, 1, 5, 21, domain parts, and RID
                    rid = sid_parts[-1]
                    if rid in COMMON_DEFAULT_GROUP_RIDS.values():
                        return SOURCE_OBJECT_CATEGORIES["Group_CommonDefault"]
    
    # Check if source type exists in categories
    if source_type in SOURCE_OBJECT_CATEGORIES:
        return SOURCE_OBJECT_CATEGORIES[source_type]
    
    # Handle list types (check for known types in the list)
    if isinstance(source_type, list):
        for label in source_type:
            if label in SOURCE_OBJECT_CATEGORIES:
                return SOURCE_OBJECT_CATEGORIES[label]
    
    return SOURCE_OBJECT_CATEGORIES["default"]


def get_relationship_type_risk(relationship_type):
    """
    Get risk category for relationship type.
    
    Args:
        relationship_type: String name of the relationship type
        
    Returns:
        Risk category value (int)
    """
    return RELATIONSHIP_TYPE_CATEGORIES.get(
        relationship_type,
        RELATIONSHIP_TYPE_CATEGORIES["default"]
    )


def get_target_object_risk(target_labels):
    """
    Get risk category for target object based on its labels.
    
    NOTE: Common default groups are NOT considered for target objects.
    All target groups use the standard "Group" risk category regardless of name.
    Common default group logic only applies to SOURCE objects.
    
    Args:
        target_labels: List of labels for the target object (e.g., ["Base", "Group"])
        
    Returns:
        Risk category value (int)
    """
    if not target_labels:
        return TARGET_OBJECT_CATEGORIES["default"]
    
    # Check each label and return the highest risk category found
    # NOTE: We do NOT check for common default group names - all groups get same risk as targets
    max_risk = TARGET_OBJECT_CATEGORIES["default"]
    for label in target_labels:
        if label in TARGET_OBJECT_CATEGORIES:
            max_risk = max(max_risk, TARGET_OBJECT_CATEGORIES[label])
    
    return max_risk


def get_affected_paths_multiplier(affected_paths):
    """
    Get multiplier for affected attack paths.
    
    Args:
        affected_paths: Number of affected attack paths (int)
        
    Returns:
        Multiplier value (float)
    """
    for min_paths, max_paths, multiplier in AFFECTED_ATTACK_PATHS_MULTIPLIERS:
        if min_paths <= affected_paths < max_paths:
            return multiplier
    
    # Fallback (shouldn't happen)
    return 1.0


def validate_risk_categories():
    """
    Validate that all risk category values are between 1 and 10.
    Raises ValueError if any value is outside this range.
    """
    errors = []
    
    # Validate source object categories
    for category, value in SOURCE_OBJECT_CATEGORIES.items():
        if not (1 <= value <= 10):
            errors.append(f"SOURCE_OBJECT_CATEGORIES['{category}'] = {value} is not between 1 and 10")
    
    # Validate relationship type categories
    for category, value in RELATIONSHIP_TYPE_CATEGORIES.items():
        if not (1 <= value <= 10):
            errors.append(f"RELATIONSHIP_TYPE_CATEGORIES['{category}'] = {value} is not between 1 and 10")
    
    # Validate target object categories
    for category, value in TARGET_OBJECT_CATEGORIES.items():
        if not (1 <= value <= 10):
            errors.append(f"TARGET_OBJECT_CATEGORIES['{category}'] = {value} is not between 1 and 10")
    
    if errors:
        error_msg = "Risk category validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    return True


def calculate_risk_score_range():
    """
    Calculate the theoretical minimum and maximum risk scores based on current configuration.
    This function dynamically calculates min/max based on:
    - Current risk category values
    - Current weights
    - Current path multipliers
    
    Returns:
        tuple: (min_score, max_score) as floats
    """
    # Get min/max values from each category
    min_source = min(SOURCE_OBJECT_CATEGORIES.values())
    max_source = max(SOURCE_OBJECT_CATEGORIES.values())
    
    min_relationship = min(RELATIONSHIP_TYPE_CATEGORIES.values())
    max_relationship = max(RELATIONSHIP_TYPE_CATEGORIES.values())
    
    min_target = min(TARGET_OBJECT_CATEGORIES.values())
    max_target = max(TARGET_OBJECT_CATEGORIES.values())
    
    # Get min/max path multipliers
    min_path_multiplier = min(multiplier for _, _, multiplier in AFFECTED_ATTACK_PATHS_MULTIPLIERS)
    max_path_multiplier = max(multiplier for _, _, multiplier in AFFECTED_ATTACK_PATHS_MULTIPLIERS)
    
    # Calculate weighted min/max
    weights = RISK_WEIGHTS
    
    min_score = (
        weights["source_object"] * min_source +
        weights["relationship_type"] * min_relationship +
        weights["target_object"] * min_target +
        weights["affected_attack_paths"] * min_path_multiplier * 10
    )
    
    max_score = (
        weights["source_object"] * max_source +
        weights["relationship_type"] * max_relationship +
        weights["target_object"] * max_target +
        weights["affected_attack_paths"] * max_path_multiplier * 10
    )
    
    return min_score, max_score


def normalize_risk_score(risk_score):
    """
    Normalize risk score to a 1-100 scale for easier interpretation.
    
    Uses linear scaling to map the theoretical risk range (calculated dynamically)
    to a 1-100 scale. This makes risk scores more intuitive and easier to communicate.
    
    The min/max range is calculated dynamically based on current configuration,
    so it adapts automatically if users change weights or risk category values.
    
    Formula: normalized = 1 + ((risk_score - min_score) / (max_score - min_score)) * 99
    
    Args:
        risk_score: Raw risk score (float)
        
    Returns:
        Normalized risk score (int) from 1 to 100
    """
    min_score, max_score = calculate_risk_score_range()
    
    # Handle edge cases
    if max_score == min_score:
        # All scores would be the same, return 50 (middle of 1-100)
        return 50
    
    if risk_score <= min_score:
        return 1
    if risk_score >= max_score:
        return 100
    
    # Linear normalization: map [min_score, max_score] to [1, 100]
    normalized = 1 + ((risk_score - min_score) / (max_score - min_score)) * 99
    return round(normalized)


# Validate risk categories on module import
# This ensures all values are between 1 and 10 before the module is used
try:
    validate_risk_categories()
except ValueError as e:
    import sys
    print(f"ERROR: Invalid risk category configuration:\n{e}", file=sys.stderr)
    print("\nPlease ensure all risk category values are between 1 and 10.", file=sys.stderr)
    sys.exit(1)



