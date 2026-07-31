import streamlit as st


def style_background_home():
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #5865F2 !important;
            }

            .stApp div[data-testid="stColumn"] {
                background-color: #E0E3FF !important;
                padding: 2.5rem !important;
                border-radius: 5rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_background_dashboard():
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #E0E3FF !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_base_layout():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Climate+Crisis:YEAR@1979&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap');
            /* Hide the main menu and footer */
                
            #MainMenu,footer,header{
                visibility: hidden;
            }

            .block-container {
                padding-top: 1rem !important;
            }

            h1{
                font-family: 'Climate Crisis', sans-serif !important;
                font-size: 3.8rem !important;
                line-height: 1 !important;
                margin-bottom: 0rem !important;
                letter-spacing: 0.05em !important;
            }

            h2{
                font-family: 'Climate Crisis', sans-serif !important;
                font-size: 2rem !important;
                line-height: 1 !important;
                margin-bottom: 0rem !important;
                letter-spacing: 0.05em !important;
                # color: #071645 !important;
            }

            h3,h4,p{
                font-family: 'Outfit', sans-serif !important;
            }

            button[kind="primary"] {
                background-color:#5865F2 !important;
                border-radius: 1.5rem !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                tranisiton: transform 0.25s ease-in-out !important;
            }
            
            button[kind="secondary"] {
                background-color:#EB459E !important;
                border-radius: 1.5rem !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                tranisiton: transform 0.25s ease-in-out !important;
            }
            button[kind="tertiary"] {
                background-color:black !important;
                border-radius: 1.5rem !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                tranisiton: transform 0.25s ease-in-out !important;
            }
            button:hover {
                transform: scale(1.05) !important;
            }

            /* Custom modern styling for all Alert Boxes (st.error, st.warning, st.info, st.success) */
            div[data-testid="stAlert"] {
                border-radius: 1.25rem !important;
                padding: 0.85rem 1.25rem !important;
                font-family: 'Outfit', sans-serif !important;
                font-weight: 500 !important;
                border: 1.5px solid transparent !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03) !important;
                margin-top: 0.75rem !important;
                margin-bottom: 0.75rem !important;
            }

            div[data-testid="stAlert"] p {
                font-family: 'Outfit', sans-serif !important;
                font-size: 0.95rem !important;
                font-weight: 600 !important;
            }

            /* Error alert box styling */
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentError"]) {
                background-color: #FFEAEF !important;
                border-color: #FF4D6D !important;
                color: #C0113B !important;
            }
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentError"]) p {
                color: #C0113B !important;
            }

            /* Warning alert box styling */
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentWarning"]) {
                background-color: #FFF8E7 !important;
                border-color: #FFB703 !important;
                color: #B45309 !important;
            }
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentWarning"]) p {
                color: #B45309 !important;
            }

            /* Success alert box styling */
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentSuccess"]) {
                background-color: #E8F8F5 !important;
                border-color: #2ECC71 !important;
                color: #117A65 !important;
            }
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentSuccess"]) p {
                color: #117A65 !important;
            }

            /* Info alert box styling */
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentInfo"]) {
                background-color: #EEF2FF !important;
                border-color: #6366F1 !important;
                color: #3730A3 !important;
            }
            div[data-testid="stAlert"]:has(div[data-testid="stNotificationContentInfo"]) p {
                color: #3730A3 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
