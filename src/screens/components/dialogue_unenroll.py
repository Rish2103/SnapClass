import streamlit as st
from src.database.db import unenroll_student_to_subject


@st.dialog("⚠️ Confirm Unenrollment")
def confirm_unenroll_dialog(subject_name, subject_code, student_id, subject_id):
    st.markdown(
        f"""
        <div style="text-align:center; padding: 5px;">
            <div style="font-size: 3rem; margin-bottom: 5px;">🗑️</div>
            <h3 style="color:#071645; margin:0 0 10px 0; font-family:'Outfit', sans-serif;">Are you sure?</h3>
            <p style="color:#64748b; font-size: 1rem; font-family:'Outfit', sans-serif;">
                You are about to unenroll from <b>{subject_name}</b> (<span style="background:#E0E3FF; color:#5865F2; padding:2px 8px; border-radius:5px;">{subject_code}</span>).
            </p>
            <div style="background:#FFEAEF; color:#C0113B; border:1.5px solid #FF4D6D; padding:10px; border-radius:12px; font-size:0.9rem; font-weight:600; margin:15px 0;">
                ⚠️ This will remove your attendance record access for this course.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="primary", width="stretch", key="cancel_unenroll_btn"):
            st.rerun()
    with col2:
        if st.button("Yes, Unenroll", type="secondary", width="stretch", key="confirm_unenroll_btn", icon=":material/delete:"):
            with st.spinner("Unenrolling..."):
                unenroll_student_to_subject(student_id, subject_id)
                st.toast(f"Unenrolled from {subject_name}", icon=":material/check:")
                import time

                time.sleep(1)
                st.rerun()
