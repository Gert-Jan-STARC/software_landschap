import streamlit as st
from methodes.custom_methodes import remove_top_margin

remove_top_margin()
pages = {
"CRUD": [
    st.Page("menu/add.py", title="Add node", icon="➕"),
    st.Page("menu/edit.py", title="Edit node", icon="✏️"),
]
}
    
pg = st.navigation(pages)
pg.run()
