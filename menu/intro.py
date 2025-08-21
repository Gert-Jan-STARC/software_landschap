import streamlit as st

st.set_page_config(layout="wide")

st.subheader("Welcome to the Software Landscape App!")
st.write("This app allows you to manage and visualize your software landscape using a graph database.")
st.write("You can add nodes representing software, companies, roles, and categories, and create relations between them.")
st.write("Use the navigation menu to explore different functionalities:")
st.write("- **All nodes**: View all existing nodes in the graph.")  
st.write("- **Add node**: Add new nodes to the graph.")
st.write("- **Edit node**: Modify existing nodes.")
st.write("- **Add relation**: Create relations between nodes.")
st.write("For more information on how to use the app, please refer to the documentation or contact support.")
st.write("You can also view the graph model below to understand the relationships between different node types.")
st.image("images/Graph Model.png", use_container_width=True)