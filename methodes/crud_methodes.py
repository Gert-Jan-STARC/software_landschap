from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
import os
import re
from typing import Any, Dict, List, Optional

class GraphCrud:
    """Thin convenience wrapper around the Neo4j Python driver.

    Reads connection settings from environment and offers small helpers for
    common CRUD and aggregation operations used by the app.
    """

    def __init__(self):
        """Initialize the Neo4j driver using environment variables."""
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri:
            raise ValueError("Environment variable NEO4J_URI is not set.")
        if not username:
            raise ValueError("Environment variable NEO4J_USERNAME is not set.")
        if not password:
            raise ValueError("Environment variable NEO4J_PASSWORD is not set.")

        # Optional tuning via env
        def _int_env(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, default))
            except Exception:
                return default

        pool_size = _int_env("NEO4J_MAX_POOL_SIZE", 100)
        conn_timeout = _int_env("NEO4J_CONNECTION_TIMEOUT", 30)
        max_lifetime = _int_env("NEO4J_MAX_CONN_LIFETIME", 3600)

        self._driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_pool_size=pool_size,
            connection_timeout=conn_timeout,
            max_connection_lifetime=max_lifetime,
        )

    # ---------- driver lifecycle ----------

    def close(self):
        """Close the Neo4j driver connection."""
        self._driver.close()

    def is_alive(self) -> bool:
        """Simple connectivity check against the database."""
        try:
            with self._driver.session() as session:
                res = session.run("RETURN 1 AS ok").single()
                return bool(res and res["ok"] == 1)
        except Exception:
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ---------- internal helpers ----------
    @staticmethod
    def _quote_label(label: str) -> str:
        """Validate and quote a label for Cypher to avoid injection/typos."""
        s = label.strip() if isinstance(label, str) else ""
        if not s or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s):
            raise ValueError(f"Invalid label name: {label!r}")
        return f"`{s}`"

    @staticmethod
    def _quote_reltype(rel_type: str) -> str:
        s = rel_type.strip() if isinstance(rel_type, str) else ""
        if not s or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s):
            raise ValueError(f"Invalid relationship type: {rel_type!r}")
        return f"`{s}`"

    # ==========================
    # Node CRUD Operations
    # ==========================

    def clear_database(self) -> None:
        """Delete all nodes and relationships in the database."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def create_node(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        """
        Create or update a node with the given label.
        First tries to find an existing node by label + name.
        If found, updates it. Otherwise, creates a new node.
        Uses MERGE for creation to avoid warnings.
        """
        if not properties.get('emailaddress') and not properties.get('name'):
            raise ValueError("At least one of 'emailaddress' or 'name' must be provided for matching.")
        with self._driver.session() as session:
            qlabel = self._quote_label(label)
            # Step 1: Check if node with same label + name exists
            existing_node = None
            if properties.get('name'):
                check_query = f"""
                MATCH (n:{qlabel} {{name: $name}})
                RETURN elementId(n) AS node_id
                """
                existing_node = session.run(check_query, name=properties['name']).single()
            if existing_node:
                # Step 2: Update existing node
                update_query = """
                MATCH (n) WHERE elementId(n) = $node_id
                SET n += $props
                RETURN elementId(n) AS node_id
                """
                result = session.run(update_query, node_id=existing_node['node_id'], props=properties).single()
                return result["node_id"]
            # Step 3: Create new node using MERGE (prefer emailaddress if available)
            if properties.get('emailaddress'):
                merge_key = "emailaddress"
                merge_value = properties['emailaddress']
            else:
                merge_key = "name"
                merge_value = properties['name']
            create_query = f"""
            MERGE (n:{qlabel} {{{merge_key}: $merge_value}})
            ON CREATE SET n += $props
            ON MATCH SET n += $props
            RETURN elementId(n) AS node_id
            """
            result = session.run(create_query, merge_value=merge_value, props=properties).single()
            return result["node_id"]

    def insert_node(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        """
        Insert-only variant: creates a new node if and only if no node with
        the same label and 'name' exists. If one exists, do nothing and
        return None.

        Returns the new node's elementId when inserted, or None when skipped.
        """
        name = properties.get('name')
        if not name:
            raise ValueError("'name' must be provided for insert_node().")

        with self._driver.session() as session:
            qlabel = self._quote_label(label)

            # Check if a node with this name already exists
            check_query = f"""
            MATCH (n:{qlabel} {{name: $name}})
            RETURN elementId(n) AS node_id
            """
            existing = session.run(check_query, name=name).single()
            if existing:
                return None  # Skip insert

            # Create fresh node
            create_query = f"""
            CREATE (n:{qlabel})
            SET n += $props
            RETURN elementId(n) AS node_id
            """
            result = session.run(create_query, props=properties).single()
            return result["node_id"] if result else None
    
    def get_nodes_by_type(self, node_type: str) -> List[str]:
        nodes = set()
        with self._driver.session() as session:
            qlabel = self._quote_label(node_type)
            query = f"""
            MATCH (n:{qlabel})
            RETURN DISTINCT n.name AS name
            ORDER BY name
            """
            result = session.run(query)
            for record in result:
                if record["name"]:
                    nodes.add(record["name"])

        return sorted(list(nodes))
    
    def read_node_properties_by_name(self, label: str, name: str) -> Optional[Dict[str, Any]]:
        """Read properties of a node based on its label and name."""
        with self._driver.session() as session:
            qlabel = self._quote_label(label)
            query = (
                f"MATCH (n:{qlabel}) "
                f"WHERE n.name = $name "
                f"RETURN properties(n) AS props"
            )
            result = session.run(query, name=name).single()
            return result['props'] if result else None
        
    def delete_node(self, label: str, name: str) -> bool:
        """
        Delete a node by its label and name property.
        Returns True if a node was deleted, False if none matched.
        """
        if not name:
            raise ValueError("'name' must be provided to delete a node.")

        with self._driver.session() as session:
            qlabel = self._quote_label(label)
            # Use summary counters to reliably detect deletions
            query = f"MATCH (n:{qlabel} {{name: $name}}) DETACH DELETE n"
            result = session.run(query, name=name)
            summary = result.consume()
            return getattr(summary.counters, 'nodes_deleted', 0) > 0
        
    # ==========================
    # Aggregations / Counts
    # ==========================

    def count_nodes(self, label: str) -> int:
        """Return the number of nodes with the given label."""
        with self._driver.session() as session:
            query = f"MATCH (n:{self._quote_label(label)}) RETURN count(n) AS c"
            result = session.run(query).single()
            return int(result["c"]) if result else 0

    def total_nodes(self) -> int:
        """Return the total number of nodes in the database."""
        with self._driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS c").single()
            return int(result["c"]) if result else 0

    def count_relationships(self, rel_type: str) -> int:
        """Return the number of relationships of a given type."""
        with self._driver.session() as session:
            query = f"MATCH ()-[r:{self._quote_reltype(rel_type)}]-() RETURN count(r) AS c"
            result = session.run(query).single()
            return int(result["c"]) if result else 0

    def total_relationships(self) -> int:
        """Return the total number of relationships in the database."""
        with self._driver.session() as session:
            result = session.run("MATCH ()-[r]-() RETURN count(r) AS c").single()
            return int(result["c"]) if result else 0

    def counts_by_labels(self, labels: List[str]) -> Dict[str, int]:
        """Return a dict of label -> count for the provided labels."""
        counts: Dict[str, int] = {}
        for label in labels:
            try:
                counts[label] = self.count_nodes(label)
            except Exception:
                counts[label] = 0
        return counts
        
    def create_relation_by_name(
        self,
        start_label: str,
        start_name: str,
        end_label: str,
        end_name: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a relationship between two nodes identified by name."""
        with self._driver.session() as session:
            a = self._quote_label(start_label)
            b = self._quote_label(end_label)
            r = self._quote_reltype(relationship_type)
            query = (
                f"MATCH (a:{a} {{name: $start_name}}), "
                f"(b:{b} {{name: $end_name}}) "
                f"MERGE (a)-[r:{r}]->(b) "
                f"SET r += $properties "
                f"RETURN elementId(r) AS rel_id"
            )
            result = session.run(
                query,
                start_name=start_name,
                end_name=end_name,
                properties=properties or {}
            ).single()
            return result["rel_id"] if result else None
    

            
if __name__ == "__main__":
    # Example usage
    crud = GraphCrud()
    
    crud.insert_node("company", {"name": "Autodesk", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Graphisoft", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Trimble", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Solibri", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "KUBUS", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Dalux", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "PlanRadar", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "KYP", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Bluebeam", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "SCIA", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "MagiCAD Group", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Elecosoft", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Ed Controls", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Pro4all (Snagstream)", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Asite", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Catenda", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Thinkproject", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Oracle (Aconex)", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Bentley Systems", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Bricsys", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Vectorworks (Design Express)", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "simplebim", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Revizto", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "BIM Track", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Cadac Group", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Zutec", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "IDEA StatiCa", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Arkance systems", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Planon", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Neanex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Brink software", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Allplan", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Dassault Systems", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Esri", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Jedox", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Kadaster", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Move3 software", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Unity  Technologies", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Arkance Systems NL", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Weaver B.V.", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Bimforce", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Neanex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Linear GMBH", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "ISD Group", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Arkey Systems", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "2Jours B.V", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "De twee snoeken", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "EZ-base BV", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Squadra", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "ZeeBoer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Masters in Process B.V.", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Spacewell", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Cleverstone", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "RadarAdvies", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "XSARUS", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Blender Foundation", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "Open Design Alliance", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "VIKTOR", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "McNeel", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("company", {"name": "DAQS", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})

    crud.insert_node("software", {"name": "Construction Cloud (ACC)", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Trimble Connect", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Asite CDE", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Catenda Hub (Bimsync)", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Thinkproject CDE", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Oracle Aconex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Bentley ProjectWise", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Bricsys 24/7", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "TheModus Suite", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Cadac Organice", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIMcollab Cloud", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIMcollab ZOOM", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Solibri Office", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Navisworks", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Revizto", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIM Track", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "simplebim", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Dalux Field/Box", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "PlanRadar", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Ed Controls", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Snagstream", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Bluebeam Revu/Cloud", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Zutec Handover", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Powerproject", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "KYP Project", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "IBIS-TRAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Autodesk Revit", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Archicad", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Tekla Structures", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Vectorworks Architect", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BricsCAD BIM", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "OpenBuildings Designer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "DDScad", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Stabicad", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "MagiCAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "SCIA Engineer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "IDEA StatiCa", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Solibri Anywhere", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Dalux BIM Viewer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Jedox", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "SmartTeam", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Quintiq", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "AutoCAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "ArcGIS", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Civil 3D", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Solidworks", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "DuboCalc", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Sketchup", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Klic App", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Synchro4D", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Primavera P6", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Tilos", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "MathCAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Ibis", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Planon IWMS", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Horizons", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Vault", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "StabiCAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Unity Virtual Reality", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Solibri model viewer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "InfraCAD", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Vabi EPA-U / BIM  / Elements", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "DGMR / Bink", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Weaver CMDB", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Humble MJOP", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "EDcontrol", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "TiQiT", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Project wise", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Vertex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Real estate RE suite", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Powerproject", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Neanex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Linear", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "KUBUS spexx", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Infraworks", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Ibis4projects", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "HiCad", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BricsCad", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Catenda Hub", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIMcollab", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIM-meetstaten", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Asite", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Areddo", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Adomi", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Advance", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "12Build", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "2Jours", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Calago", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Bouwconnekt / 2 snoeken", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "EZ-base", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "MatrixFrame", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Squadra", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Utopis PIM", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIMlink", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Ilips", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Spacewell Axxerion", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "GRIP", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Gebouw365 - Radar advies", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Briefbuilder", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Xsarus", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "IFC viewer", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Oracle Aconex", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Allplan", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "BIMcollab Zoom", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "OMRT", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Viktor", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "Grasshopper", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
    crud.insert_node("software", {"name": "DAQS.io", "address": "test", "website": "test", "telefoonnummer": "test", "emailaddress": "test", "description": "test"})
