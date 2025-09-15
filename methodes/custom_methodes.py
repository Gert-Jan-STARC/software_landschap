import streamlit as st
from methodes.crud_methodes import GraphCrud

# Provide a single, cached GraphCrud instance across reruns to avoid
# repeatedly reconnecting to Neo4j. Use a versioned factory so we can
# invalidate the cache when the implementation changes.
CRUD_CACHE_VERSION = "2025-09-15-01"

@st.cache_resource(show_spinner=False)
def _crud_factory(_version: str) -> GraphCrud:
    return GraphCrud()

def get_crud() -> GraphCrud:
    return _crud_factory(CRUD_CACHE_VERSION)

# datamodels for each node type
node_configuration = {
    "business_capability": {"naam": "str", "omschrijving": "txt"},
    "software_bedrijf": {"naam": "str", "adres": "str", "website": "str", "telefoonnummer": "str", "e-mailadres":"str"},
    "applicatie": {"naam": "str", "omschrijving": "txt"},
    "keten_rol": {"naam": "str", "omschrijving": "txt"},
    "standaard": {"naam": "str", "beheer_organisatie": "str"},
    "waarde_stroom_fase": {"naam": "str", "omschrijving": "txt"},
    "waarde_stroom": {"name": "str", "description": "txt"}
}

#relation types for graphdb
relation_configuration = {
    "ONDERSTEUNT_BIJ": {"node_1": "applicatie", "node_2": "business_capability", "properties": {}},
    "GEBRUIKT": {"node_1": "keten_rol", "node_2": "applicatie", "properties": {}},
    "MAAKT": {"node_1": "software_bedrijf", "node_2": "applicatie", "properties": {}},
    "MAAKT_GEBRUIKT_VAN": {"node_1": "applicatie", "node_2": "standaard", "properties": {}},
    "WORDT_GEBRUIKT_IN": {"node_1": "applicatie", "node_2": "waarde_stroom_fase", "properties": {}},
    "WERKT_IN": {"node_1": "keten_rol", "node_2": "waarde_stroom_fase", "properties": {}},
    "IS_ONDERDEEL_VAN": {"node_1": "waarde_stroom_fase", "node_2": "waarde_stroom", "properties": {}},
    "HEEFT": {"node_1": "keten_rol", "node_2": "business_capability", "properties": {}},
    "IS_NODIG_IN": {"node_1": "business_capability", "node_2": "waarde_stroom_fase", "properties": {}}
}

def remove_top_margin():
    remove_top_margin = """
        <style>
            /* Hide top header */
            [data-testid="stMainMenu"] {
                display: none;
            }
            /* Hide top header */
            [data-testid="stStatusWidget"] {
                display: none;
            }
            /* Hide stAppDeployButton */
            [data-testid="stAppDeployButton"] {
                display: none;
            }

            /* Remove top margin by adjusting padding */
            div.block-container {
                padding-top: 40px;
            }
        </style>"""
    st.markdown(remove_top_margin, unsafe_allow_html=True)

def clear_edit_state(prefix: str | None = None) -> None:
    """Clear common edit-related Streamlit state keys.

    - Always clears: confirm_delete, edit_node, edit_category, existing_node_*.
    - If prefix is provided, also clears keys starting with "{prefix}_".
    """
    try:
        keys_to_clear = []
        for k in list(st.session_state.keys()):
            if k in ("confirm_delete", "edit_node", "edit_category"):
                keys_to_clear.append(k)
            if k.startswith("existing_node_"):
                keys_to_clear.append(k)
            if prefix and k.startswith(f"{prefix}_"):
                keys_to_clear.append(k)
        for k in set(keys_to_clear):
            del st.session_state[k]
    except Exception:
        pass

@st.dialog("Are you sure?")
def delete_proceed(nodes, keyid, name):
    st.checkbox(f"I'm sure I want to delete node {nodes} with {keyid}: {name}", key="confirm_delete")
    if st.button("Delete forever!", use_container_width=True, type="primary"):
        if not st.session_state.get("confirm_delete", False):
            st.error("You must check the box to confirm deletion.")
            return
        else:
            st.success("Profile deleted successfully!")
            get_crud().delete_node(nodes, name)
            # Invalidate cached reads so UI reflects changes immediately
            try:
                st.cache_data.clear()
            except Exception:
                pass
            # Centralized clearing of edit-related UI state
            clear_edit_state(nodes)
        st.rerun()
