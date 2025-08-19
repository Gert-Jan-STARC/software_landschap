import streamlit as st
from methodes.crud_methodes import GraphCrud
from methodes.custom_methodes import relation_configuration

crud = GraphCrud()

st.subheader("Add a new relation here.")
relation_type = st.selectbox("Select relation type", relation_configuration.keys())
if relation_type != "":
    with st.form(f"add_{relation_type}_form", clear_on_submit=True):
        st.subheader(f"Add a new {relation_type}")

        # Select node types for the relation
        node_1_type = relation_configuration[relation_type]["node_1"]
        node_2_type = relation_configuration[relation_type]["node_2"]

        # Get existing nodes for each type
        node_1_options = crud.get_nodes_by_type(node_1_type)
        node_2_options = crud.get_nodes_by_type(node_2_type)

        # Select nodes for the relation
        node_1 = st.selectbox(f"Select {node_1_type}", options=node_1_options, key=f"{relation_type}_node_1")
        node_2 = st.selectbox(f"Select {node_2_type}", options=node_2_options, key=f"{relation_type}_node_2")

        # Generate input for properties if any
        properties = relation_configuration[relation_type].get("properties", {})
        if properties:
            st.subheader("Properties for the relation")
            for prop in properties:
                if properties[prop] == "str":
                    st.text_input(prop, key=f"{relation_type}_{prop}")
                elif properties[prop] == "txt":
                    st.text_area(prop, key=f"{relation_type}_{prop}")
                elif isinstance(properties[prop], list):
                    st.selectbox(prop, options=properties[prop], key=f"{relation_type}_{prop}") 

        # Submit button to create the relation
        if st.form_submit_button(f"Add {relation_type}", icon="➕", use_container_width=True, type="primary"):
            if node_1 and node_2:
                crud.create_relation_by_name(
                    start_label=node_1_type,
                    start_name=node_1,
                    end_label=node_2_type,
                    end_name=node_2,
                    relationship_type=relation_type,
                    properties={prop: st.session_state.get(f"{relation_type}_{prop}", "") for prop in properties}
                )
                st.success(f"{relation_type} added successfully!")
            else:
                st.error("Please select both nodes for the relation.")
