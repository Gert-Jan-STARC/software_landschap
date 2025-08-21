import streamlit as st
from methodes.crud_methodes import GraphCrud
from methodes.custom_methodes import node_configuration, delete_proceed

crud = GraphCrud()

st.subheader("Add a new node here.")
node_type = st.selectbox("Select node type", node_configuration.keys())

if node_type != "":
    with st.form(f"add_{node_type}_form", clear_on_submit=True):
        
        st.subheader(f"Add a new {node_type}")
        for key, value in node_configuration[node_type].items():
            if value == "str":
                st.text_input(key, key=f"{node_type}_{key}")
            elif value == "txt":
                st.text_area(key, key=f"{node_type}_{key}")
            elif isinstance(value, list):
                st.selectbox(key, options=value, key=f"{node_type}_{key}")
        
        st.divider()
        if st.form_submit_button(f"Add {node_type}", icon="➕", use_container_width=True, type="primary"):
            if all(st.session_state.get(f"{node_type}_{key}") for key in node_configuration[node_type].keys()):
                crud.create_node(node_type, {key: st.session_state[f"{node_type}_{key}"] for key in node_configuration[node_type].keys()})
                st.success(f"{node_type} added successfully!")
            else:
                st.error("Please fill in all required text fields: " + ", ".join(node_configuration[node_type].keys()))