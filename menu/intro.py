import streamlit as st
from methodes.custom_methodes import get_crud

st.set_page_config(layout="wide")

crud = get_crud()

st.subheader("Welcome to the Software Landscape App!")
st.write("This app allows you to manage and visualize your software landscape using a graph database.")
st.write("You can add nodes representing software, companies, roles, and categories, and create relations between them.")
st.write("Use the navigation menu to explore different functionalities:")
st.write("- **All nodes**: View all existing nodes in the graph.")
st.write("- **Add node**: Add new nodes to the graph.")
st.write("- **Edit node**: Modify existing nodes.")
st.write("- **Add relation**: Create relations between nodes.")

st.divider()
st.subheader("Dashboard")

# Quick refresh clears caches to force requery
if st.button("Refresh data", use_container_width=False):
    try:
        st.cache_data.clear()
    except Exception:
        pass
    st.rerun()

db_error = False

@st.cache_data(ttl=60, show_spinner=False)
def load_dashboard_metrics():
    c = get_crud()
    return {
        "software": c.count_nodes("software"),
        "company": c.count_nodes("company"),
        "role": c.count_nodes("role"),
        "nodes": c.total_nodes(),
        "rels": c.total_relationships(),
    }

try:
    with st.spinner("Loading dashboard metrics..."):
        metrics = load_dashboard_metrics()
        software_count = metrics["software"]
        company_count = metrics["company"]
        role_count = metrics["role"]
        total_nodes = metrics["nodes"]
        total_rels = metrics["rels"]
except Exception:
    db_error = True
    software_count = company_count = role_count = total_nodes = total_rels = 0

if db_error or not crud.is_alive():
    st.warning("Database not reachable yet. Please start Neo4j and click Refresh.")

cols = st.columns(5)
with cols[0]:
    st.metric("Total Software", f"{software_count}")
with cols[1]:
    st.metric("Total Companies", f"{company_count}")
with cols[2]:
    st.metric("Total Roles", f"{role_count}")
with cols[3]:
    st.metric("All Nodes", f"{total_nodes}")
with cols[4]:
    st.metric("All Relationships", f"{total_rels}")
    
