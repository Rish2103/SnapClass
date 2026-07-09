import streamlit as st


def footer_home():

    # --- FOOTER SECTION ---
    st.markdown("---")

    st.markdown(
        """
        <div style="text-align: center; padding: 10px; color: #ffffff; font-size: 14px;">
            Created with ❤️ by <span style="font-weight: bold; color: #071645;">Rishabh</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer_dashboard():

    # --- FOOTER SECTION ---

    st.markdown(
        """
        <div style="text-align: center; padding: 10px; color: black; font-size: 14px;">
            Created with ❤️ by <span style="font-weight: bold; color: black;">Rishabh</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
