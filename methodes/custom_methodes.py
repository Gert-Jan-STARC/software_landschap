import streamlit as st

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