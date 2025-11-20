"""
Configuration file for Neo4j connection settings.
Adjust these values to match your BloodHound instance.
"""

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "bloodhoundcommunityedition"

# Default output filename (will be used if not specified via command line)
DEFAULT_OUTPUT_FILENAME = "ChokeHound_report.xlsx"

# Limit for "Critical Choke Points Risk" query (number of results to return)
# It is recommended to keep this value at 200 (default) unless you
# have a specific need and sufficient computational resources.
LIMIT_CHOKE_POINTS = 200

# Hop limit for "Critical Choke Points Risk" query (maximum number of hops to traverse when finding origins)
# WARNING: Increasing this value beyond 2 or 3 can significantly increase query execution time,
# especially in large Active Directory environments. The query complexity grows exponentially
# with each additional hop. It is recommended to keep this value at 3 maximum (default) unless you
# have a specific need and sufficient computational resources.
CHOKE_POINTS_HOP_LIMIT = 3