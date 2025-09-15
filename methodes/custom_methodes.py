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
    "category": {"name": "str"},
    "company": {"name": "str", "address": "str", "website": "str", "telefoonnummer": "str", "emailaddress":"str", "description": "txt"},
    "fase": {"name": "str", "description": "txt"},
    "role": {"name": "str", "description": "txt"},
    "software": {"name": "str", "description": "txt"}
}

#relation types for graphdb
relation_configuration = {
    "CREATES": {"node_1": "company", "node_2": "software", "properties": {}},
    "USES": {"node_1": "role", "node_2": "software", "properties": {}},
    "HAS": {"node_1": "software", "node_2": "category", "properties": {}},
    "USED_IN": {"node_1": "software", "node_2": "fase", "properties": {}},
    "WORKS_IN": {"node_1": "role", "node_2": "fase", "properties": {}},
    "NEXT": {"node_1": "fase", "node_2": "fase", "properties": {}},
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
