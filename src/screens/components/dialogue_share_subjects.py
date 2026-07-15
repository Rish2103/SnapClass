import streamlit as st
from src.database.db import create_subject, check_subject_exists

import segno
import io

@st.dialog("Share Class Link")
def share_subject_dialog(subject_name,subject_code):
    app_domain = "snapclass-main.streamlit.app"
    join_url = f"{app_domain}/?join-code={subject_code}"
    
    st.header("Scan to Join")

    qr = segno.make_qr(join_url)
    
    out = io.BytesIO()
    
    qr.save(out,kind='png',scale=10,border=1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Copy Link")
        st.code(join_url,language='text')
        st.code(subject_code,language='text')
        st.info("Copy this link to share on WhatsApp or Email")
        
    with col2:
        st.markdown("### Scan to Join")
        st.image(out.getvalue(),width=200,caption='QR Code for class sharing')