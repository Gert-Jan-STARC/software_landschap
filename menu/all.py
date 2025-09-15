import streamlit as st
from methodes.custom_methodes import node_configuration, delete_proceed, get_crud

st.set_page_config(layout="centered")

crud = get_crud()
if "edit_node" not in st.session_state:
    st.session_state.edit_node = ""
if "edit_category" not in st.session_state:
    st.session_state.edit_category = ""

st.subheader("Select nodes here.")
node_type = st.selectbox("Select node type", node_configuration.keys())

st.subheader("Existing nodes")
for existing_node in crud.get_nodes_by_type(node_type):
    col1, col2, col3 = st.columns([10,1,1])  # wide left column, small right columns

    with col1:
        st.write(existing_node)

    with col2:
        if st.button("", icon="✏️", key=f"edit_{node_type}_{existing_node}", help="Edit"):
            st.session_state.edit_node = existing_node
            st.session_state.edit_category = node_type
            st.switch_page("menu/edit.py")

    with col3:
        deleted = st.button("", icon="🗑️", key=f"delete_{node_type}_{existing_node}", help="Delete")
        if deleted:
            delete_proceed(node_type, "name", existing_node)
