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
from src.pipelines.face_pipeline import (
    get_face_embedding,
    train_classifier,
    verify_blink_liveness,
    check_duplicate_face,
)
from src.database.db import update_student_face_embedding
from src.screens.components.dialogue_enroll import create_subject_dialog
from src.screens.components.dialogue_unenroll import confirm_unenroll_dialog

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
        total_cls = stats["total"]
        att_cls = stats["attended"]
        pct_val = (att_cls / total_cls * 100.0) if total_cls > 0 else 100.0
        is_safe = pct_val >= 75.0

        def unenroll_btn(subject_name=sub["name"], subject_code=sub["subject_code"], subject_id=sid, student_id_val=student_id):
            if st.button(
                "Unenroll from the course",
                type="tertiary",
                width="stretch",
                key=f"unenroll_{subject_id}",
                icon=":material/delete:",
            ):
                confirm_unenroll_dialog(subject_name, subject_code, student_id_val, subject_id)

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
                pct_badge=(pct_val, is_safe),
            )

    st.space()
    with st.expander("👤 Update your Registered Face Scan", expanded=False):
        st.info("Re-scan your face to update your AI recognition profile.")
        rescan_photo = st.camera_input("Take a fresh photo to update your face scan", key="rescan_cam")
        if rescan_photo:
            rescan_img = np.array(Image.open(rescan_photo))
            with st.spinner("Processing new facial features..."):
                encs = get_face_embedding(rescan_img)
                if encs:
                    res = update_student_face_embedding(student_id, encs[0].tolist())
                    if res is not None:
                        train_classifier()
                        st.success("🎉 Facial profile updated successfully!")
                    else:
                        st.error("⚠️ Supabase Permission Setup Required: Database UPDATE policy is disabled on table 'students'.")
                        st.markdown(
                            """
                            <div style="background:#FFF3CD; padding:15px; border-radius:12px; border-left:5px solid #FFC107; margin-top:10px;">
                              <b>To enable face profile updates</b>, paste this SQL in your <b>Supabase Dashboard &rarr; SQL Editor</b>:
                              <pre style="background:#282C34; color:#61AFEF; padding:10px; border-radius:8px; margin-top:8px;">ALTER TABLE students DISABLE ROW LEVEL SECURITY;</pre>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.error("Could not extract facial features. Please ensure your face is well-lit.")

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
        <p style="text-align:center; color:#555; font-size:14px;">
          🔐 Two-step liveness verification to keep your account secure
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.space()

    # Initialize blink challenge state
    if "blink_step" not in st.session_state:
        st.session_state.blink_step = 1
        st.session_state.blink_img_open = None

    # --- Start Over button ---
    if st.session_state.blink_step == 2:
        if st.button("↩ Start Over", type="secondary", key="blink_start_over"):
            st.session_state.blink_step = 1
            st.session_state.blink_img_open = None
            st.rerun()

    show_registration = False

    # ===== STEP 1: Eyes Open Photo =====
    if st.session_state.blink_step == 1:
        st.info("**Step 1 of 2**: Take a photo with your **eyes open** (look normally at the camera)")

        photo_open = st.camera_input(
            "Step 1: Take a photo with eyes OPEN", key="cam_eyes_open", label_visibility="visible"
        )

        if photo_open:
            img_open = np.array(Image.open(photo_open))

            with st.spinner("Checking face..."):
                detected, all_ids, num_faces, *rest = predict_attendance(img_open)

                if num_faces == 0:
                    st.warning("No face detected! Please make sure your face is clearly visible.")
                elif num_faces > 1:
                    st.warning("Multiple faces detected! Please make sure only your face is visible.")
                else:
                    # Face found — store and move to step 2
                    st.session_state.blink_img_open = img_open
                    st.session_state.blink_step = 2
                    st.rerun()

    # ===== STEP 2: Eyes Closed Photo =====
    elif st.session_state.blink_step == 2:
        st.success("✅ Step 1 complete — face detected!")
        st.info("**Step 2 of 2**: Now **close your eyes** and take another photo")

        photo_closed = st.camera_input(
            "Step 2: Close your eyes and take a photo", key="cam_eyes_closed", label_visibility="visible"
        )

        if photo_closed:
            img_closed = np.array(Image.open(photo_closed))
            img_open = st.session_state.blink_img_open

            with st.spinner("Verifying liveness..."):
                is_live, reason, details = verify_blink_liveness(img_open, img_closed)

            if not is_live:
                st.error(f"⚠️ Liveness check failed: {reason}")
                st.caption("Please click **Start Over** and try again.")
                # Reset for next attempt
                st.session_state.blink_step = 1
                st.session_state.blink_img_open = None
            else:
                # Liveness passed — now identify the student
                st.success("✅ Liveness verified! Identifying you...")

                with st.spinner("Matching your face..."):
                    detected, all_ids, num_faces, *rest = predict_attendance(img_open)

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
                        # Clean up blink state
                        st.session_state.blink_step = 1
                        st.session_state.blink_img_open = None

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
                    # Reset blink state
                    st.session_state.blink_step = 1
                    st.session_state.blink_img_open = None

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
                        img = st.session_state.get("blink_img_open")
                        if img is None:
                            img = np.array(Image.open(photo_closed))

                        encodings = get_face_embedding(img)

                        if encodings:
                            is_dup, dup_name = check_duplicate_face(encodings[0])
                            if is_dup:
                                st.error(f"⚠️ Registration Blocked: This facial profile is already registered under student account '{dup_name}'!")
                            else:
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

