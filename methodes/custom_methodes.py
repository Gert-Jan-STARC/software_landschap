import streamlit as st
from methodes.crud_methodes import GraphCrud

crud = GraphCrud()

#datamodels for each node type
node_configuration = {
    "category": {"name": "str"},
    "company": {"name": "str", "address": "str", "website": "str", "telefoonnummer": "str", "emailaddress":"str", "description": "txt"},
    "fase": {"name": "str", "description": "txt"},
    "role": {"name": "str", "description": "txt"},
    "software": {"name": "str", "description": "txt", "subscription model": ["Flat rate", "Tiered pricing", "Usage-Based", "Freemium", "Feature-Based"]}
}

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

@st.dialog("Are you sure?")
def delete_proceed(nodes, keyid, name):
    st.checkbox(f"I'm sure I want to delete node {nodes} with {keyid}: {name}", key="confirm_delete")
    if st.button("Delete forever!", use_container_width=True, type="primary"):
        if not st.session_state.get("confirm_delete", False):
            st.error("You must check the box to confirm deletion.")
            return
        else:
            st.success("Profile deleted successfully!")
            crud.delete_node(nodes, name)
            if name in st.session_state:
                for key in st.session_state.keys():
                    del st.session_state[key]
        st.rerun()