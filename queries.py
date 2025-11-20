"""
Cypher queries for finding choke points in Active Directory.
These queries are executed against Neo4j after BloodHound data collection.
"""

import config

# List of relationship types used in queries
RELATIONSHIP_TYPES = [
    "Owns", "GenericAll", "GenericWrite", "WriteOwner", "WriteDacl", "MemberOf",
    "ForceChangePassword", "AllExtendedRights", "AddMember", "HasSession", "GPLink",
    "AllowedToDelegate", "CoerceToTGT", "AllowedToAct", "AdminTo", "CanPSRemote",
    "CanRDP", "ExecuteDCOM", "HasSIDHistory", "AddSelf", "DCSync", "ReadLAPSPassword",
    "ReadGMSAPassword", "DumpSMSAPassword", "SQLAdmin", "AddAllowedToAct", "WriteSPN",
    "AddKeyCredentialLink", "SyncLAPSPassword", "WriteAccountRestrictions", "WriteGPLink",
    "GoldenCert", "ADCSESC1", "ADCSESC3", "ADCSESC4", "ADCSESC6a", "ADCSESC6b",
    "ADCSESC9a", "ADCSESC9b", "ADCSESC10a", "ADCSESC10b", "ADCSESC13", "SyncedToEntraUser",
    "CoerceAndRelayNTLMToSMB", "CoerceAndRelayNTLMToADCS", "WriteOwnerLimitedRights",
    "OwnsLimitedRights", "ClaimSpecialIdentity", "CoerceAndRelayNTLMToLDAP",
    "CoerceAndRelayNTLMToLDAPS", "ContainsIdentity", "PropagatesACEsTo", "GPOAppliesTo",
    "CanApplyGPO", "HasTrustKeys", "ManageCA", "ManageCertificates", "Contains", "DCFor",
    "SameForestTrust", "SpoofSIDHistory", "AbuseTGTDelegation"
]


def get_relationship_pattern():
    """Returns the relationship pattern string for use in Cypher queries."""
    return "|".join(RELATIONSHIP_TYPES)


QUERIES = {
    "Critical Choke Points Risk": """
        // Step 1: identify all direct edges into Tier-0 (choke candidates)
        MATCH (src)-[r:{}]->(t:Tag_Tier_Zero)
        WHERE NOT src:Tag_Tier_Zero
        WITH DISTINCT src, t, type(r) AS RelationshipType

        // Step 2: for each choke edge, find all non–Tier-0 origins that can reach src (up to {} hops)
        MATCH p = (o)-[:{}*0..{}]->(src)
        WHERE NOT o:Tag_Tier_Zero
        // make sure no Tier-0 nodes appear in the origin→src path
        AND ALL(n IN nodes(p) WHERE NOT n:Tag_Tier_Zero)

        // Step 3: aggregate & rank choke edges by how many unique origins can reach them
        WITH src, t, RelationshipType, count(DISTINCT o) AS ReachableOrigins
        RETURN
            src.name AS SourceName,
            labels(src) AS SourceType,
            src.objectid AS SourceObjectID,
            src.distinguishedname AS SourceDN,
            RelationshipType,
            t.name AS TargetName,
            labels(t) AS TargetType,
            t.objectid AS TargetObjectID,
            t.distinguishedname AS TargetDN,
            ReachableOrigins AS AffectedAttackPaths
        
        LIMIT {}
    """.format(get_relationship_pattern(), config.CHOKE_POINTS_HOP_LIMIT, get_relationship_pattern(), config.CHOKE_POINTS_HOP_LIMIT, config.LIMIT_CHOKE_POINTS),

    # Rank relationship types that directly hit Tier-0 (first-degree)
    # This shows which relationship types into Tier-0 are most common (i.e. edge-type choke points).
    "Direct relationships into Tier0": """
        MATCH (src)-[r]->(dst:Tag_Tier_Zero)
        WHERE NOT src:Tag_Tier_Zero
        RETURN type(r) AS RelationshipType,
            count(DISTINCT src.name + '|' + dst.name) AS DistinctSourceTargetPairs,
            count(*) AS TotalEdges
        ORDER BY DistinctSourceTargetPairs DESC, TotalEdges DESC
    """,

    # Rank source nodes that directly connect to Tier-0
    # This finds the top non-Tier nodes that directly have the most Tier-0 targets
    # — good immediate choke points (e.g., an account/group that has admin on many Tier-0 objects).
    "Source nodes into T0 Rank": """
        MATCH (src)-[r]->(dst:Tag_Tier_Zero)
        WHERE NOT src:Tag_Tier_Zero
        RETURN src.name AS SourceNode,
            labels(src) AS SourceType,
            src.objectid AS SourceObjectID,
            src.distinguishedname AS SourceDN,
            count(DISTINCT dst.name) AS DistinctTier0Targets,
            collect(DISTINCT type(r)) AS RelationshipTypes
        ORDER BY DistinctTier0Targets DESC, SourceNode
        LIMIT 100
    """
}

