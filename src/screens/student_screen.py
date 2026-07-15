import streamlit as st
from PIL import Image
import numpy as np

from src.screens.ui.base_layout import (
    style_background_home,
    style_base_layout,
    style_background_dashboard,
)
from src.screens.components.header import header_home, header_dashboard
from src.screens.components.footer import footer_home, footer_dashboard

from src.pipelines.face_pipeline import predict_attendance
from src.database.db import get_all_students, create_student

from src.pipelines.voice_pipeline import get_voice_embedding
from src.pipelines.face_pipeline import get_face_embedding, train_classifier

from src.screens.components.dialogue_enroll import create_subject_dialog

from src.database.db import (
    get_student_subjects,
    get_student_attendance,
    unenroll_student_to_subject,
)

from src.screens.components.subject_card import subject_card


def student_dashbard():
    student_data = st.session_state.student_data
    student_id = student_data["student_id"]
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {student_data['name']}!""")
        if st.button(
            "Logout",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace",
        ):
            st.session_state["is_logged_in"] = False
            del st.session_state.student_data
            st.rerun()

    st.space()

    c1, c2 = st.columns(2)
    with c1:
        st.header("Your Enrolled Subjects")
    with c2:
        if st.button("Enroll in Subject", width="stretch", type="primary"):
            create_subject_dialog()

    st.divider()

    with st.spinner("Loading your enrolled subjects.."):
        subject = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}

    for log in logs:
        sid = log["subject_id"]

        if sid not in stats_map:
            stats_map[sid] = {"total": 0, "attended": 0}

        stats_map[sid]["total"] += 1

        if log.get("is_present"):
            stats_map[sid]["attended"] += 1

    cols = st.columns(2)
    for i, sub_node in enumerate(subject):
        sub = sub_node["subjects"]
        sid = sub_node["subject_id"]

        stats = stats_map.get(sid, {"total": 0, "attended": 0})

        def unenroll_btn(subject_id=sid, student_id_val=student_id):
            if st.button(
                "Unenroll from the course",
                type="tertiary",
                width="stretch",
                key=f"unenroll_{subject_id}",
                icon=":material/delete:",
            ):
                unenroll_student_to_subject(student_id_val, subject_id)
                st.success("Unenrolled successfully!")
                import time

                time.sleep(1)
                st.rerun()

        with cols[i % 2]:
            subject_card(
                name=sub["name"],
                code=sub["subject_code"],
                section=sub["section"],
                stats=[
                    ("🗓️", "Total", stats["total"]),
                    ("✅", "Attended", stats["attended"]),
                ],
                footer_callback=unenroll_btn,
            )

    footer_dashboard()


def student_screen():
    style_background_dashboard()
    style_base_layout()

    if "student_data" in st.session_state:
        student_dashbard()
        return

    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        if st.button(
            "Go back to Home",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace",
        ):
            st.session_state["login_type"] = None
            st.rerun()

    st.markdown(
        """
        <h2 style="color:#071645; text-align:center;">Login using Face Recognition</h2>
        """,
        unsafe_allow_html=True,
    )

    st.space()
    st.space()

    show_registration = False
    photo_source = st.camera_input(
        "Take a picture of your face to login", label_visibility="visible"
    )

    if photo_source:
        img = np.array(Image.open(photo_source))

        with st.spinner("AI is scanning.."):
            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning("Face not found!")
            elif num_faces > 1:
                st.warning("Multiple faces found!")
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    all_students = get_all_students()

                    student = next(
                        (
                            s
                            for s in all_students
                            if s.get("student_id") == student_id
                            or s.get("id") == student_id
                        ),
                        None,
                    )

                    if student:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "student"
                        st.session_state.student_data = student
                        st.toast(f"Welcome Back {student['name']}")
                        import time

                        time.sleep(1)
                        st.rerun()

                else:
                    st.error("Face not recognized! You might be a new student")
                    show_registration = True

    if show_registration:
        with st.container(border=True):
            st.header("Register new Profile")
            new_name = st.text_input("Enter your name", placeholder="E.g. Rishabh Shah")

            st.subheader("Optional : Voice Enrollment")
            st.info("Enroll for voice only attendance")

            audio_data = None

            try:
                audio_data = st.audio_input(
                    "Record a short phrase like I am present, my name is Aakash etc."
                )
            except Exception as e:
                st.error("Audio Data failed")

            if st.button("Create Account", type="primary"):
                if new_name:
                    with st.spinner("Creating profile.."):
                        img = np.array(Image.open(photo_source))
                        encodings = get_face_embedding(img)
                        if encodings:
                            face_emb = encodings[0].tolist()

                            voice_emb = None
                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(
                                new_name,
                                face_embedding=face_emb,
                                voice_embedding=voice_emb,
                            )

                            if response_data:
                                train_classifier()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = "student"
                                st.session_state.student_data = response_data[0]
                                st.toast(f"Profile Created! Hi {new_name}")
                                import time

                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error(
                                "Couldn't capture your facial features for facial recognition!"
                            )
                else:
                    st.warning("Please enter your name!")
    footer_dashboard()
