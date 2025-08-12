from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
import os

class GraphCrud:
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

        self._driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        """Close the Neo4j driver connection."""
        self._driver.close()

    # ==========================
    # Node CRUD Operations
    # ==========================

    def clear_database(self):
        """Delete all nodes and relationships in the database."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def create_node(self, label, properties):
        """
        Create or update a node with the given label.
        First tries to find an existing node by label + name.
        If found, updates it. Otherwise, creates a new node.
        Uses MERGE for creation to avoid warnings.
        """
        if not properties.get('emailaddress') and not properties.get('name'):
            raise ValueError("At least one of 'emailaddress' or 'name' must be provided for matching.")

        with self._driver.session() as session:
            # Step 1: Check if node with same label + name exists
            existing_node = None
            if properties.get('name'):
                check_query = f"""
                MATCH (n:{label} {{name: $name}})
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
            MERGE (n:{label} {{{merge_key}: $merge_value}})
            ON CREATE SET n += $props
            ON MATCH SET n += $props
            RETURN elementId(n) AS node_id
            """
            result = session.run(create_query, merge_value=merge_value, props=properties).single()
            return result["node_id"]

        
    def delete_node(self, label, name):
        """
        Delete a node by its label and name property.
        Returns True if a node was deleted, False if none matched.
        """
        if not name:
            raise ValueError("'name' must be provided to delete a node.")

        with self._driver.session() as session:
            query = f"""
            MATCH (n:{label} {{name: $name}})
            DETACH DELETE n
            RETURN COUNT(n) AS deleted_count
            """
            result = session.run(query, name=name).single()
            return result["deleted_count"] > 0
        
    def create_relationship(self, start_label, start_name, end_label, end_name, relationship_type, properties=None):
        """Create a relationship between two nodes identified by name."""
        with self._driver.session() as session:
            query = (
                f"MATCH (a:{start_label} {{name: $start_name}}), "
                f"(b:{end_label} {{name: $end_name}}) "
                f"MERGE (a)-[r:{relationship_type}]->(b) "
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
    crud.clear_database()
    crud.create_node("fase", {"name": "Initiatief", "description": 
    "Wat gebeurt er? Eerste idee of behoefte aan woningen (door gemeente, ontwikkelaar, corporatie of particulier). "
    "Globale verkenning van de locatie, haalbaarheid en doelgroepen. "
    "Belangrijke activiteiten: Locatieonderzoek (bestemmingsplan, eigendom, omgevingsfactoren). Marktanalyse en indicatie "
    "van kosten/baten. Globaal programma van eisen (hoeveel woningen, type, duurzaamheid)."})

    crud.create_node("fase", {"name": "Haalbaarheid", "description": 
    "Wat gebeurt er? Uitwerken van een eerste ontwerpconcept en kostenraming. Toetsen of het plan financieel, technisch, "
    "juridisch en maatschappelijk haalbaar is. "
    "Belangrijke activiteiten: Stedenbouwkundig schetsontwerp. Overleg met gemeente en andere stakeholders. "
    "Eventuele participatie met omwonenden. Risicoanalyse. Opstellen businesscase."})

    crud.create_node("fase", {"name": "Ontwerp", "description": 
    "Wat gebeurt er? Van schetsontwerp naar definitief ontwerp. "
    "Belangrijke activiteiten: Schetsontwerp (SO) ruimtelijke opzet, massa en situering. "
    "Voorlopig Ontwerp (VO): materialen, plattegronden, gevels. Definitief Ontwerp (DO): alle details, constructies en installaties uitgewerkt. "
    "Duurzaamheids- en energieconcept."})

    crud.create_node("fase", {"name": "Vergunning", "description": 
    "Wat gebeurt er? Aanvragen van de Omgevingsvergunning (bouw, milieu, eventueel sloop). "
    "Plan wordt formeel getoetst aan het bestemmingsplan, bouwbesluit, welstand. "
    "Belangrijke activiteiten: Indienen complete aanvraag bij de gemeente. Eventuele bezwaarprocedures door derden. Definitieve goedkeuring verkrijgen."})

    crud.create_node("fase", {"name": "Engineering", "description": 
    "Wat gebeurt er? Selecteren van aannemer (aanbesteding of onderhandse gunning). Opstellen contracten. "
    "Belangrijke activiteiten: Werkvoorbereiding door de aannemer (uitvoeringsplannen, inkoop materialen). "
    "Eventueel bouwrijp maken van de grond (nutsvoorzieningen, infrastructuur)."})

    crud.create_node("fase", {"name": "Uitvoering", "description": 
    "Wat gebeurt er? Fysieke bouw van de woningen. "
    "Belangrijke activiteiten: Grondwerk, fundering, ruwbouw, afbouw. Kwaliteitscontroles en bouwtoezicht. "
    "Eventuele aanpassingen tijdens de bouw."})

    crud.create_node("fase", {"name": "Oplevering", "description": 
    "Wat gebeurt er? Officiële overdracht van woningen aan kopers/huurders. "
    "Belangrijke activiteiten: Eindinspectie en opleverrapport. Verhelpen van opleverpunten. Overdracht documentatie (garanties, handleidingen)."})

    crud.create_node("fase", {"name": "Beheer", "description": 
    "Wat gebeurt er? Ondersteuning bewoners bij gebreken. Eventuele garantieclaims. "
    "Belangrijke activiteiten: Nazorgperiode (meestal 3–6 maanden of 1 jaar). Overdracht aan VvE of beheerorganisatie."})

    crud.create_relationship("fase", "Initiatief", "fase", "Haalbaarheid", "NEXT", {} )
    crud.create_relationship("fase", "Haalbaarheid", "fase", "Ontwerp", "NEXT", {})
    crud.create_relationship("fase", "Ontwerp", "fase", "Vergunning", "NEXT", {})
    crud.create_relationship("fase", "Vergunning", "fase", "Engineering", "NEXT ", {})
    crud.create_relationship("fase", "Engineering", "fase", "Uitvoering", "NEXT", {})
    crud.create_relationship("fase", "Uitvoering", "fase", "Oplevering", "NEXT", {})
    crud.create_relationship("fase", "Oplevering", "fase", "Beheer", "NEXT", {})

    crud.create_node("role", {"name": "Opdrachtgever", "description": 
        "De partij die het project financiert en initieert, bijvoorbeeld een gemeente, corporatie of projectontwikkelaar."})
    crud.create_node("role", {"name": "Projectontwikkelaar", "description": 
        "Coördineert en ontwikkelt het bouwproject van initiatief tot oplevering."})
    crud.create_node("role", {"name": "Woningcorporatie", "description": 
        "Organisatie die woningen bouwt en beheert, vaak gericht op sociale huur."})
    crud.create_node("role", {"name": "Gemeenteambtenaar", "description": 
        "Beoordeelt plannen en verleent vergunningen namens de gemeente."})
    crud.create_node("role", {"name": "Planoloog", "description": 
        "Specialist in ruimtelijke ordening en beleidskaders rondom bouwprojecten."})
    crud.create_node("role", {"name": "Vastgoedadviseur", "description": 
        "Adviseert over marktwaarde, financiering en exploitatie van vastgoed."})
    crud.create_node("role", {"name": "Stedenbouwkundige", "description": 
        "Ontwerpt de ruimtelijke opzet van een gebied, inclusief infrastructuur en inrichting."})
    crud.create_node("role", {"name": "Adviseur Ruimtelijke Ordening", "description": 
        "Begeleidt juridische en beleidsmatige aspecten van ruimtelijke plannen."})
    crud.create_node("role", {"name": "Financieel adviseur", "description": 
        "Analyseert en adviseert over financiële haalbaarheid en investeringen."})
    crud.create_node("role", {"name": "Architect", "description": 
        "Maakt het ontwerp van de woning en de uitstraling ervan."})
    crud.create_node("role", {"name": "Constructeur", "description": 
        "Zorgt dat het ontwerp technisch veilig en uitvoerbaar is."})
    crud.create_node("role", {"name": "Adviseur installaties", "description": 
        "Ontwerpt technische installaties zoals verwarming, ventilatie en elektra."})
    crud.create_node("role", {"name": "Duurzaamheidsexpert", "description": 
        "Adviseert over energiebesparing, milieuvriendelijke materialen en technieken."})
    crud.create_node("role", {"name": "Welstandscommissie", "description": 
        "Beoordeelt of het ontwerp voldoet aan esthetische en ruimtelijke kwaliteitseisen."})
    crud.create_node("role", {"name": "Jurist / Vergunningenadviseur", "description": 
        "Ondersteunt bij juridische procedures en vergunningaanvragen."})
    crud.create_node("role", {"name": "Omgevingsmanager", "description": 
        "Beheert communicatie en belangen van omwonenden en stakeholders."})
    crud.create_node("role", {"name": "Aannemer", "description": 
        "Voert de bouw uit en draagt zorg voor het bouwproces."})
    crud.create_node("role", {"name": "Werkvoorbereider", "description": 
        "Bereidt de uitvoering voor, regelt planning, materialen en logistiek."})
    crud.create_node("role", {"name": "Inkoopmanager", "description": 
        "Verantwoordelijk voor de aanschaf van materialen en diensten."})
    crud.create_node("role", {"name": "Adviseur bouwlogistiek", "description": 
        "Plant en optimaliseert het transport en opslag op de bouwplaats."})
    crud.create_node("role", {"name": "Uitvoerder", "description": 
        "Toezicht op de dagelijkse gang van zaken op de bouwplaats."})
    crud.create_node("role", {"name": "Bouwplaatsmedewerker", "description": 
        "Voert praktische bouwwerkzaamheden uit."})
    crud.create_node("role", {"name": "Veiligheidscoördinator (VGM)", "description": 
        "Zorgt voor naleving van veiligheids-, gezondheids- en milieuregels."})
    crud.create_node("role", {"name": "Kwaliteitsinspecteur", "description": 
        "Controleert of het werk voldoet aan de afgesproken kwaliteitseisen."})
    crud.create_node("role", {"name": "Opzichter", "description": 
        "Houdt toezicht namens opdrachtgever op het bouwproces."})
    crud.create_node("role", {"name": "Koper / Bewoner", "description": 
        "Eindgebruiker van de woning."})
    crud.create_node("role", {"name": "Beheerder / VvE beheerder", "description": 
        "Beheert het onderhoud en de gemeenschappelijke zaken van een wooncomplex."})
    crud.create_node("role", {"name": "Service- en onderhoudsbedrijf", "description": 
        "Voert reparaties en onderhoudswerkzaamheden uit na oplevering."})
    crud.create_node("role", {"name": "Klantcontact / Klachtenafhandeling", "description": 
        "Behandelt vragen, meldingen en klachten van bewoners."})

    # Initiatief
    crud.create_relationship("role", "Opdrachtgever", "fase", "Initiatief", "WORKS_IN", {})
    crud.create_relationship("role", "Projectontwikkelaar", "fase", "Initiatief", "WORKS_IN", {})
    crud.create_relationship("role", "Woningcorporatie", "fase", "Initiatief", "WORKS_IN", {})
    crud.create_relationship("role", "Gemeenteambtenaar", "fase", "Initiatief", "WORKS_IN", {})

    # Haalbaarheid
    crud.create_relationship("role", "Projectontwikkelaar", "fase", "Haalbaarheid", "WORKS_IN", {})
    crud.create_relationship("role", "Opdrachtgever", "fase", "Initiatief", "WORKS_IN", {})
    crud.create_relationship("role", "Financieel adviseur", "fase", "Haalbaarheid", "WORKS_IN", {})
    crud.create_relationship("role", "Planoloog", "fase", "Haalbaarheid", "WORKS_IN", {})
    crud.create_relationship("role", "Stedenbouwkundige", "fase", "Haalbaarheid", "WORKS_IN", {})
    crud.create_relationship("role", "Vastgoedadviseur", "fase", "Haalbaarheid", "WORKS_IN", {})

    # Ontwerp
    crud.create_relationship("role", "Architect", "fase", "Ontwerp", "WORKS_IN", {})
    crud.create_relationship("role", "Opdrachtgever", "fase", "Initiatief", "WORKS_IN", {})
    crud.create_relationship("role", "Constructeur", "fase", "Ontwerp", "WORKS_IN", {})
    crud.create_relationship("role", "Adviseur installaties", "fase", "Ontwerp", "WORKS_IN", {})
    crud.create_relationship("role", "Duurzaamheidsexpert", "fase", "Ontwerp", "WORKS_IN", {})
    crud.create_relationship("role", "Welstandscommissie", "fase", "Ontwerp", "WORKS_IN", {})

    # Vergunning
    crud.create_relationship("role", "Gemeenteambtenaar", "fase", "Vergunning", "WORKS_IN", {})
    crud.create_relationship("role", "Jurist / Vergunningenadviseur", "fase", "Vergunning", "WORKS_IN", {})
    crud.create_relationship("role", "Omgevingsmanager", "fase", "Vergunning", "WORKS_IN", {})

    # Engineering
    crud.create_relationship("role", "Aannemer", "fase", "Engineering", "WORKS_IN", {})
    crud.create_relationship("role", "Werkvoorbereider", "fase", "Engineering", "WORKS_IN", {})
    crud.create_relationship("role", "Inkoopmanager", "fase", "Engineering", "WORKS_IN", {})
    crud.create_relationship("role", "Adviseur bouwlogistiek", "fase", "Engineering", "WORKS_IN", {})

    # Uitvoering
    crud.create_relationship("role", "Aannemer", "fase", "Uitvoering", "WORKS_IN", {})
    crud.create_relationship("role", "Uitvoerder", "fase", "Uitvoering", "WORKS_IN", {})
    crud.create_relationship("role", "Bouwplaatsmedewerker", "fase", "Uitvoering", "WORKS_IN", {})
    crud.create_relationship("role", "Veiligheidscoördinator (VGM)", "fase", "Uitvoering", "WORKS_IN", {})
    crud.create_relationship("role", "Kwaliteitsinspecteur", "fase", "Uitvoering", "WORKS_IN", {})
    crud.create_relationship("role", "Opzichter", "fase", "Uitvoering", "WORKS_IN", {})

    # Oplevering
    crud.create_relationship("role", "Opdrachtgever", "fase", "Oplevering", "WORKS_IN", {})
    crud.create_relationship("role", "Koper / Bewoner", "fase", "Oplevering", "WORKS_IN", {})
    crud.create_relationship("role", "Opzichter", "fase", "Oplevering", "WORKS_IN", {})

    # Beheer
    crud.create_relationship("role", "Beheerder / VvE beheerder", "fase", "Beheer", "WORKS_IN", {})
    crud.create_relationship("role", "Service- en onderhoudsbedrijf", "fase", "Beheer", "WORKS_IN", {})
    crud.create_relationship("role", "Klantcontact / Klachtenafhandeling", "fase", "Beheer", "WORKS_IN", {})
    crud.create_relationship("role", "Koper / Bewoner", "fase", "Beheer", "WORKS_IN", {})



    # crud.delete_node("software", "Neo4j")