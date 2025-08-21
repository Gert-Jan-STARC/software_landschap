import streamlit as st
from methodes.custom_methodes import remove_top_margin

remove_top_margin()
st.set_page_config(layout="centered")

st.logo(image="images/logo.png", link="https://www.digigo.nu", size="medium")

pages = {
    "Home": [st.Page("menu/intro.py", title="Home", icon="🏠")],
    "CRUD": [
        st.Page("menu/all.py", title="All nodes", icon="📋"),
        st.Page("menu/add.py", title="Add node", icon="➕"),
        st.Page("menu/edit.py", title="Edit node", icon="✏️"),
        st.Page("menu/relation.py", title="Add relation", icon="🔗"),
    ]
}
    
pg = st.navigation(pages)
pg.run()
