from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from src.database.db import create_teacher
from src.screens.ui.base_layout import (
    style_background_home,
    style_base_layout,
    style_background_dashboard,
)
from src.screens.components.header import header_home, header_dashboard
from src.screens.components.footer import footer_home, footer_dashboard

from src.database.db import check_teacher_exists
from src.database.db import create_teacher
from src.database.db import teacher_login
from src.database.db import get_teacher_subjects
from src.database.db import get_teacher_by_username, get_teacher_by_email, verify_security_answer, update_teacher_password, validate_password_strength

from src.screens.components.dialogue_create_subjects import create_subject_dialog
from src.screens.components.subject_card import subject_card

from src.screens.components.dialogue_share_subjects import share_subject_dialog
from src.screens.components.dialogue_add_photo import add_photos_dialog

from src.database.config import supabase

from src.pipelines.face_pipeline import predict_attendance
from src.screens.components.dialogue_attendance_results import attendance_result_dialog
from src.screens.components.dialogue_voice_attendance import voice_attendance_logs

from src.database.db import get_attendance_for_teacher


def teacher_screen():
    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()

    elif (
        "teacher_login_type" not in st.session_state
        or st.session_state.teacher_login_type == "login"
    ):
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()
    elif st.session_state.teacher_login_type == "forgot_password":
        teacher_screen_forgot_password()


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {teacher_data['name']}!""")
        if st.button(
            "Logout",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace",
        ):
            st.session_state["is_logged_in"] = False
            del st.session_state.teacher_data
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = "take attendance"

    tab1, tab2, tab3 = st.columns(3)

    with tab1:
        type1 = (
            "primary"
            if st.session_state.current_teacher_tab == "take_attendance"
            else "tertiary"
        )
        if st.button(
            "Take Attendance", type=type1, width="stretch", icon=":material/ar_on_you:"
        ):
            st.session_state.current_teacher_tab = "take_attendance"
            st.rerun()
    with tab2:
        type2 = (
            "primary"
            if st.session_state.current_teacher_tab == "manage_subjects"
            else "tertiary"
        )
        if st.button(
            "Manage Subjects",
            type=type2,
            width="stretch",
            icon=":material/book_ribbon:",
        ):
            st.session_state.current_teacher_tab = "manage_subjects"
            st.rerun()
    with tab3:
        type3 = (
            "primary"
            if st.session_state.current_teacher_tab == "attendance_records"
            else "tertiary"
        )
        if st.button(
            "Attendance Records",
            type=type3,
            width="stretch",
            icon=":material/cards_stack:",
        ):
            st.session_state.current_teacher_tab = "attendance_records"
            st.rerun()

    st.divider()

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()

    footer_dashboard()


def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    st.header("Take AI Attendance")

    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning("You havent created any subjects yet! Please create one to begin!")
        return

    subject_options = {
        f"{s['name']} - {s['subject_code']}": s["subject_id"] for s in subjects
    }

    col1, col2 = st.columns([2.5, 1], vertical_alignment="bottom")

    with col1:
        selected_subject_label = st.selectbox(
            "Select Subject", options=list(subject_options.keys())
        )
    with col2:
        if st.button(
            "Add Photos",
            type="primary",
            icon=":material/photo_prints:",
            width="stretch",
        ):
            add_photos_dialog()

    if selected_subject_label is None:
        return

    selected_subject_id = subject_options[selected_subject_label]

    if st.session_state.attendance_images:
        st.header("Added Photos")
        cols = st.columns(min(3, len(st.session_state.attendance_images)))
        for idx, image in enumerate(st.session_state.attendance_images):
            with cols[idx % len(cols)]:
                st.image(image, caption=f"Photo {idx + 1}", use_container_width=True)

    has_photos = bool(st.session_state.attendance_images)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "Clear all photos",
            width="stretch",
            type="tertiary",
            icon=":material/delete:",
            disabled=not has_photos,
        ):
            st.session_state.attendance_images = []
            st.rerun()
    with c2:
        if st.button(
            "Run Face Analysis",
            width="stretch",
            type="secondary",
            icon=":material/analytics:",
            disabled=not has_photos,
        ):
            with st.spinner("Deep scanning classroom photos.."):
                all_detected_id = {}

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert("RGB"))

                    detected, *rest = predict_attendance(img_np)

                    if detected:
                        for sid in detected.keys():
                            student_id = int(sid)

                            all_detected_id.setdefault(student_id, []).append(
                                f"Photo {idx+1}"
                            )

                enrolled_res = (
                    supabase.table("subject_students")
                    .select("*,students(*)")
                    .eq("subject_id", selected_subject_id)
                    .execute()
                )
                enrolled_students = enrolled_res.data

                if not enrolled_students:
                    st.warning("No students enrolled in this course!")
                else:
                    results, attendance_to_log = [], []

                    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    for node in enrolled_students:
                        student = node["students"]
                        sources = all_detected_id.get(int(student["student_id"]), [])
                        is_present = len(sources) > 0

                        results.append(
                            {
                                "Name": student["name"],
                                "ID": student["student_id"],
                                "Source": ", ".join(sources) if is_present else "-",
                                "Status": "✅Present" if is_present else "❌ Absent",
                            }
                        )

                        attendance_to_log.append(
                            {
                                "student_id": student["student_id"],
                                "subject_id": selected_subject_id,
                                "timestamp": current_timestamp,
                                "is_present": bool(is_present),
                            }
                        )

                    attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

    with c3:
        if st.button(
            "Use Voice Attendance",
            type="primary",
            width="stretch",
            icon=":material/mic:",
        ):
            voice_attendance_logs(selected_subject_id)

    st.divider()


def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    col1, col2 = st.columns(2)
    with col1:
        st.header("Manage Subjects", width="stretch")
    with col2:
        if st.button("Create New Subject", width="stretch"):
            create_subject_dialog(teacher_id)

    # LIST ALL THE SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🧑‍🎓", "Students", sub["total_students"]),
                ("📚", "Classes", sub["total_classes"]),
            ]

            def share_button(subject=sub):
                if st.button(
                    f"Share Code: {subject['name']}",
                    key=f"share_{subject['subject_code']}",
                    icon=":material/share:",
                ):
                    share_subject_dialog(subject["name"], subject["subject_code"])

            subject_card(
                name=sub["name"],
                code=sub["subject_code"],
                section=sub["section"],
                stats=stats,
                footer_callback=share_button,
            )
            st.space()
    else:
        st.info("No subject found! Create one above.")


def teacher_tab_attendance_records():
    st.header("Attendance Records")

    teacher_id = st.session_state.teacher_data["teacher_id"]

    records = get_attendance_for_teacher(teacher_id)

    if not records:
        st.info("No attendance records found yet.")
        return

    data = []

    for r in records:
        ts = r.get("timestamp")
        dt = datetime.fromisoformat(ts) if ts else None

        data.append(
            {
                "ts_group": ts.split(".")[0] if ts else None,
                "Date": dt.strftime("%Y-%m-%d") if dt else "N/A",
                "Time_Only": dt.strftime("%I:%M %p") if dt else "N/A",
                "Time": dt.strftime("%Y-%m-%d %I:%M %p") if dt else "N/A",
                "Subject": r["subjects"]["name"],
                "Subject Code": r["subjects"]["subject_code"],
                "is_present": bool(r.get("is_present", False)),
            }
        )

    df = pd.DataFrame(data)

    summary = (
        df.groupby(["ts_group", "Date", "Time_Only", "Time", "Subject", "Subject Code"])
        .agg(Present_Count=("is_present", "sum"), Total_Count=("is_present", "count"))
        .reset_index()
    )

    summary["Attendance Stats"] = (
        "✅ "
        + summary["Present_Count"].astype(str)
        + " / "
        + summary["Total_Count"].astype(str)
        + " Students"
    )

    summary["Attendance Rate"] = (
        (summary["Present_Count"] / summary["Total_Count"] * 100).round(0).astype(int).astype(str) + "%"
    )

    display_df = summary.sort_values(by="ts_group", ascending=False)[
        ["Time", "Subject", "Subject Code", "Attendance Stats"]
    ]

    export_df = summary.sort_values(by="ts_group", ascending=False)[
        ["Date", "Time_Only", "Subject", "Subject Code", "Present_Count", "Total_Count", "Attendance Rate"]
    ].rename(columns={"Time_Only": "Time", "Present_Count": "Present Students", "Total_Count": "Total Students"})

    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        st.dataframe(display_df, width="stretch", hide_index=True)
    with col2:
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary",
            width="stretch",
            key="export_attendance_csv"
        )


def login_teacher(username, password):
    if not username or not password:
        return False
    teacher = teacher_login(username, password)
    if teacher:
        st.session_state.user_role = "teacher"
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    else:
        return False


def teacher_screen_login():
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
        <h2 style="color:#071645; text-align:center;">Login using password</h2>
        """,
        unsafe_allow_html=True,
    )

    st.space()
    st.space()

    teacher_username = st.text_input("Enter your username", key="teacher_username")
    teacher_password = st.text_input("Enter your password", type="password")

    st.markdown(
        """
        <hr style="border: 2px solid #c0c6fc; width: 100%; margin: 1.5rem 0;">
        """,
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns(2)
    login_clicked = False

    with btn_col1:
        if st.button(
            "Login",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch",
        ):
            login_clicked = True

    with btn_col2:
        if st.button(
            "Register Instead",
            type="primary",
            icon=":material/person_add:",
            shortcut="control+shift+enter",
            width="stretch",
        ):
            st.session_state.teacher_login_type = "register"
            st.rerun()

    if login_clicked:
        if login_teacher(teacher_username, teacher_password):
            st.toast("Successfully logged in as teacher", icon=":material/check:")
            import time

            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid username or password", icon=":material/error:")

    st.markdown("<div style='text-align:center; margin-top: 1rem;'>", unsafe_allow_html=True)
    if st.button("🔑 Forgot Password?", type="tertiary", key="forgot_password_link"):
        st.session_state.teacher_login_type = "forgot_password"
        if "forgot_step" in st.session_state:
            del st.session_state.forgot_step
        if "forgot_username" in st.session_state:
            del st.session_state.forgot_username
        if "forgot_teacher" in st.session_state:
            del st.session_state.forgot_teacher
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    footer_dashboard()


def register_teacher(
    teacher_username, teacher_name, teacher_pass, teacher_pass_confirm,
    security_question=None, security_answer=None, email=None
):
    if (
        not teacher_username
        or not teacher_name
        or not teacher_pass
        or not teacher_pass_confirm
    ):
        return False, "Please fill in all fields"
    if teacher_pass != teacher_pass_confirm:
        return False, "Passwords do not match"
    is_strong, strength_msg = validate_password_strength(teacher_pass)
    if not is_strong:
        return False, strength_msg
    if check_teacher_exists(teacher_username):
        return False, "Username already exists"
    if not security_question or not security_answer:
        return False, "Please set a security question and answer for password recovery"

    try:
        create_teacher(teacher_username, teacher_name, teacher_pass, security_question, security_answer, email=email)
        return True, "Successfully registered teacher"
    except Exception as e:
        return False, "Unexpected error occurred while creating teacher: " + str(e)


def teacher_screen_register():
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
        <h2 style="color:#071645; text-align:center; width: 100%;">Register your teacher profile</h2>
        """,
        unsafe_allow_html=True,
    )

    st.space()
    st.space()

    teacher_username = st.text_input("Enter your username", key="teacher_username")
    teacher_name = st.text_input("Enter your name", key="teacher_name")
    teacher_email = st.text_input("Enter your email", key="teacher_email", placeholder="e.g. teacher@school.com")
    st.caption("📧 Used to recover your account if you forget your username.")
    teacher_pass = st.text_input("Enter your password", type="password")
    st.caption("🔒 Must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number.")
    teacher_pass_confirm = st.text_input("Confirm your password", type="password")

    st.divider()
    st.markdown("**🔑 Security Question** *(for password recovery)*")

    security_questions = [
        "What is your mother's maiden name?",
        "What was the name of your first pet?",
        "What city were you born in?",
        "What is your favorite movie?",
        "What was your childhood nickname?",
        "What is the name of your favorite teacher?",
    ]
    security_question = st.selectbox(
        "Select a security question",
        options=security_questions,
        key="reg_security_question",
    )
    security_answer = st.text_input(
        "Your answer (case-insensitive)",
        key="reg_security_answer",
        placeholder="Enter your answer",
    )

    st.markdown(
        """
        <hr style="border: 2px solid #c0c6fc; width: 100%; margin: 1.5rem 0;">
        """,
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button(
            "Login Instead",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch",
        ):
            st.session_state.teacher_login_type = "login"
            st.rerun()

    with btn_col2:
        if st.button(
            "Register",
            type="primary",
            icon=":material/person_add:",
            shortcut="control+shift+enter",
            width="stretch",
        ):
            success, message = register_teacher(
                teacher_username, teacher_name, teacher_pass, teacher_pass_confirm,
                security_question, security_answer, email=teacher_email
            )
            if success:
                st.success(message)
                import time

                time.sleep(2)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)
    footer_dashboard()


SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your favorite movie?",
    "What was your childhood nickname?",
    "What is the name of your favorite teacher?",
]


def teacher_screen_forgot_password():
    """3-step forgot password flow: username → security answer → new password."""
    c1, c2 = st.columns(2, vertical_alignment="center", gap="xxlarge")
    with c1:
        header_dashboard()
    with c2:
        if st.button(
            "Back to Login",
            type="secondary",
            key="forgot_back_btn",
        ):
            st.session_state.teacher_login_type = "login"
            # Clean up forgot password state
            for key in ["forgot_step", "forgot_username", "forgot_teacher"]:
                st.session_state.pop(key, None)
            st.rerun()

    st.markdown(
        """
        <h2 style="color:#071645; text-align:center;">Reset your Password</h2>
        """,
        unsafe_allow_html=True,
    )

    st.space()

    # Initialize step
    if "forgot_step" not in st.session_state:
        st.session_state.forgot_step = 1

    # ===== STEP 1: Enter Username or Email =====
    if st.session_state.forgot_step == 1:
        st.info("**Step 1 of 3**: Enter your **username** or **email** to find your account")

        lookup_method = st.radio(
            "I want to look up my account by:",
            ["Username", "Email"],
            horizontal=True,
            key="forgot_lookup_method",
        )

        if lookup_method == "Username":
            identifier = st.text_input("Username", key="forgot_username_input", placeholder="Enter your registered username")
        else:
            identifier = st.text_input("Email", key="forgot_email_input", placeholder="Enter your registered email")

        if st.button("Next →", type="primary", key="forgot_step1_btn"):
            if not identifier:
                st.warning("Please enter your username or email")
            else:
                if lookup_method == "Username":
                    teacher = get_teacher_by_username(identifier)
                else:
                    teacher = get_teacher_by_email(identifier)

                if not teacher:
                    st.error(f"No account found with that {lookup_method.lower()}")
                elif not teacher.get("security_question"):
                    st.error("This account doesn't have a security question set. Please contact your administrator.")
                else:
                    st.session_state.forgot_username = teacher["username"]
                    st.session_state.forgot_teacher = teacher
                    st.session_state.forgot_step = 2
                    st.rerun()

    # ===== STEP 2: Answer Security Question =====
    elif st.session_state.forgot_step == 2:
        st.success("✅ Account found!")
        teacher = st.session_state.forgot_teacher
        st.info(f"**Step 2 of 3**: Answer your security question")

        st.markdown(f"**Question:** {teacher['security_question']}")
        answer = st.text_input("Your answer", key="forgot_answer_input", placeholder="Enter your answer (case-insensitive)")

        if st.button("Verify Answer →", type="primary", key="forgot_step2_btn"):
            if not answer:
                st.warning("Please enter your answer")
            else:
                is_valid, _ = verify_security_answer(st.session_state.forgot_username, answer)
                if is_valid:
                    st.session_state.forgot_step = 3
                    st.rerun()
                else:
                    st.error("Incorrect answer. Please try again.")

    # ===== STEP 3: Set New Password =====
    elif st.session_state.forgot_step == 3:
        st.success("✅ Identity verified!")
        st.info("**Step 3 of 3**: Set your new password")

        new_pass = st.text_input("New password", type="password", key="forgot_new_pass")
        confirm_pass = st.text_input("Confirm new password", type="password", key="forgot_confirm_pass")

        st.caption("Password must be at least 8 characters with uppercase, lowercase, and a number.")

        if st.button("Reset Password", type="primary", key="forgot_step3_btn"):
            if not new_pass or not confirm_pass:
                st.warning("Please fill in both password fields")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match")
            else:
                is_strong, strength_msg = validate_password_strength(new_pass)
                if not is_strong:
                    st.error(strength_msg)
                else:
                    teacher = st.session_state.forgot_teacher
                    update_teacher_password(teacher["teacher_id"], new_pass)
                    st.success("🎉 Password reset successfully! You can now login with your new password.")

                    # Clean up state
                    for key in ["forgot_step", "forgot_username", "forgot_teacher"]:
                        st.session_state.pop(key, None)

                    import time
                    time.sleep(2)
                    st.session_state.teacher_login_type = "login"
                    st.rerun()

    footer_dashboard()
