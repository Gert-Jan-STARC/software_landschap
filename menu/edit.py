import streamlit as st
from methodes.custom_methodes import node_configuration, delete_proceed, get_crud

st.set_page_config(layout="centered")

crud = get_crud()

if "edit_node" not in st.session_state:
    st.session_state.edit_node = ""
if "edit_category" not in st.session_state:
    st.session_state.edit_category = ""

st.subheader("Edit a node here.")
node_type_list = list(node_configuration.keys())
edit_catagory_index = node_type_list.index(st.session_state.edit_category) if st.session_state.edit_category in node_type_list else 0
node_type = st.selectbox("Select node type", node_type_list, index=edit_catagory_index)

selected_nodes = crud.get_nodes_by_type(node_type)
edit_node_index = selected_nodes.index(st.session_state.edit_node) if st.session_state.edit_node in selected_nodes else 0
selected_node = st.selectbox("Select existing node", options=selected_nodes, index=edit_node_index, key=f"existing_node_{node_type}")
node_properties = crud.read_node_properties_by_name(node_type, selected_node)


if node_properties:
    with st.form(f"add_{node_type}_form", clear_on_submit=False):  # don't clear, so edits stay visible
        st.subheader(f"Edit {node_type}")

        # Build inputs with pre-filled values
        for key, value in node_configuration[node_type].items():
            current_val = node_properties.get(key, "")  # default to "" if property not found

            if key in ("naam", "name"):
                name = st.text_input(key, value=current_val, key=f"{node_type}_{key}", disabled=True)
                continue

            if value == "str":
                st.text_input(key, value=current_val, key=f"{node_type}_{key}")
            elif value == "txt":
                st.text_area(key, value=current_val, key=f"{node_type}_{key}")
            elif isinstance(value, list):
                st.selectbox(
                    key,
                    options=value,
                    index=value.index(current_val) if current_val in value else 0,
                    key=f"{node_type}_{key}"
                )

        st.divider()
        if st.form_submit_button(f"Save {node_type}", icon="💾", use_container_width=True, type="primary"):
            updated_properties = {key: st.session_state[f"{node_type}_{key}"] for key in node_configuration[node_type].keys()}

            if all(updated_properties.values()):
                crud.create_node(node_type, updated_properties)
                st.success(f"{node_type} updated successfully!")
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
            else:
                st.error("Please fill in all required text fields: " + ", ".join(node_configuration[node_type].keys()))
        
    #delete node
    deleted = st.button(f"Delete {node_type}: {name}", use_container_width=True, type="secondary", icon="🗑️")
    if deleted:
        delete_proceed(node_type, "naam", name)

