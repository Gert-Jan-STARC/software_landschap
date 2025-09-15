import streamlit as st
from methodes.custom_methodes import node_configuration, delete_proceed, get_crud

st.set_page_config(layout="centered")

crud = get_crud()

st.subheader("Search nodes here.")
node_type = st.selectbox("Select node type", node_configuration.keys())
options = crud.get_nodes_by_type(node_type)
node_result = st.selectbox("Select node", options)

st.subheader(f"Search results for {node_type} > {node_result}")
if node_result:
    node_data = crud.relations_by_name(node_type, node_result)
    for key in node_data.keys():
        if key == "NEXT":
            pass
        else:
            if node_data[key]['out']:
                st.write(f"{node_result} {key} {node_data[key]['out'][0]['other_label']}")
                for item in node_data[key]['out']:
                    st.badge(item['other_name'], color="green")
            
            if node_data[key]['in']:
                st.write(f"{node_data[key]['in'][0]['other_label']} {key} {node_result}")
                for item in node_data[key]['in']:
                    st.badge(item['other_name'], color="blue")

