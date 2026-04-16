"""Utility for generating BloodHound UI exploration URLs for choke point analysis."""

import base64
from urllib.parse import quote

import chokehound.config.settings as config


def build_analysis_url(
    source_objectid: str,
    relationship_type: str,
    target_objectid: str,
    hop_limit: int = None,
) -> str:
    """
    Build a BloodHound UI URL for visualizing a choke point attack path.

    Opens BloodHound's Explore tab with a pre-filled Cypher query that shows:
      - All non-Tier-0 origins that can reach the choke point (up to hop_limit hops)
      - The direct privileged edge from the choke point to the Tier-0 target

    Args:
        source_objectid:  ObjectID of the choke point node (src)
        relationship_type: Relationship type connecting src to the Tier-0 target
        target_objectid:  ObjectID of the Tier-0 target node
        hop_limit:        Maximum hops for the upstream path traversal.
                          Defaults to AD_CHOKE_POINTS_HOP_LIMIT from settings.

    Returns:
        Fully-formed BloodHound UI URL string.
    """
    if hop_limit is None:
        hop_limit = config.AD_CHOKE_POINTS_HOP_LIMIT

    query = (
        f"MATCH (src {{objectid: '{source_objectid}'}}),"
        f"(t:Tag_Tier_Zero {{objectid: '{target_objectid}'}})\n"
        f"MATCH p1=(o)-[*0..{hop_limit}]->(src) "
        f"WHERE NOT o:Tag_Tier_Zero AND ALL(n IN nodes(p1) WHERE NOT n:Tag_Tier_Zero)\n"
        f"MATCH p2=(src)-[:{relationship_type}]->(t)\n"
        f"RETURN p1,p2 LIMIT 50"
    )

    # Base64-encode, then percent-encode so that + and = are not misinterpreted
    # by BloodHound's URL parser (+ would otherwise be decoded as a space).
    raw_b64 = base64.b64encode(query.encode("utf-8")).decode("utf-8")
    encoded = quote(raw_b64, safe="")

    base_url = config.BLOODHOUND_URI.rstrip("/")
    return (
        f"{base_url}/ui/explore"
        f"?exploreSearchTab=cypher"
        f"&cypherSearch={encoded}"
        f"&searchType=cypher"
    )
