import streamlit as st
from src.database.db import (
    create_subject,
    check_subject_exists,
    enroll_student_to_subject,
)
from src.database.config import supabase


@st.dialog("Enroll in Subject")
def create_subject_dialog():
    st.write("Enter the subject code provided by your teacher to enroll!")
    join_code = st.text_input("Subject Code", placeholder="E.g CS101")

    if st.button("Enroll now", type="primary", width="stretch"):
        if join_code:
            try:
                res = (
                    supabase.table("subjects")
                    .select("subject_id,name,subject_code")
                    .eq("subject_code", join_code)
                    .execute()
                )
                if res.data:
                    subject = res.data[0]
                    student_id = st.session_state.student_data["student_id"]

                    check = (
                        supabase.table("subject_students")
                        .select("*")
                        .eq("subject_id", subject["subject_id"])
                        .eq("student_id", student_id)
                        .execute()
                    )

                    if check.data:
                        st.warning("You are already enrolled in this subject")
                    else:
                        enroll_student_to_subject(student_id, subject["subject_id"])
                        st.success("Successfully Enrolled!")
                        import time

                        time.sleep(1)
                        st.rerun()
                else:
                    st.error(f"Subject with code '{join_code}' not found!")
            except Exception as e:
                st.error(f"Error during enrollment: {str(e)}")
        else:
            st.warning("Please enter a subject code!")
