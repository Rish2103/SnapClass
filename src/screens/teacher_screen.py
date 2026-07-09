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

from src.screens.components.dialogue_create_subjects import create_subject_dialog
from src.screens.components.subject_card import subject_card

from src.screens.components.dialogue_share_subjects import share_subject_dialog


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
        type1 = "primary" if st.session_state.current_teacher_tab == "take_attendance" else "tertiary"
        if st.button("Take Attendance", type=type1,width="stretch", icon=":material/ar_on_you:"):
            st.session_state.current_teacher_tab = "take_attendance"
            st.rerun()
    with tab2:
        type2 = "primary" if st.session_state.current_teacher_tab == "manage_subjects" else "tertiary"
        if st.button("Manage Subjects",type=type2, width="stretch", icon=":material/book_ribbon:"):
            st.session_state.current_teacher_tab = "manage_subjects"
            st.rerun()
    with tab3:
        type3 = "primary" if st.session_state.current_teacher_tab == "attendance_records" else "tertiary"
        if st.button(
            "Attendance Records",type=type3, width="stretch", icon=":material/cards_stack:"
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
    st.header("Take AI Attendance")

def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header("Manage Subjects", width='stretch')
    with col2:
        if st.button("Create New Subject", width='stretch'):
            create_subject_dialog(teacher_id)
            
    #LIST ALL THE SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🧑‍🎓","Students",sub['total_students']),
                ("📚","Classes",sub['total_classes'])
            ]
            def share_button(subject=sub):
                if st.button(f"Share Code: {subject['name']}", key=f"share_{subject['subject_code']}", icon=":material/share:"):
                    share_subject_dialog(subject['name'], subject['subject_code'])
            
            subject_card(
                name = sub['name'],
                code = sub['subject_code'],
                section = sub['section'],
                stats = stats,
                footer_callback = share_button
            )
            st.space()
    else:
        st.info("No subject found! Create one above.")

def teacher_tab_attendance_records():
    st.header("Attendance Records")

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
    with btn_col1:
        if st.button(
            "Login",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch",
        ):
            if login_teacher(teacher_username, teacher_password):
                st.toast("Successfully logged in as teacher", icon=":material/check:")
                import time

                time.sleep(2)
                st.rerun()
            else:
                st.error("Invalid username or password", icon=":material/error:")

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
    footer_dashboard()


def register_teacher(
    teacher_username, teacher_name, teacher_pass, teacher_pass_confirm
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
    if check_teacher_exists(teacher_username):
        return False, "Username already exists"

    try:
        create_teacher(teacher_username, teacher_name, teacher_pass)
        return True, "Successfully registered teacher"
    except Exception as e:
        return False, "Unexpected error occurred while creating teacher: " + str(e)

    return True, None


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
    teacher_pass = st.text_input("Enter your password", type="password")
    teacher_pass_confirm = st.text_input("Confirm your password", type="password")

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
                teacher_username, teacher_name, teacher_pass, teacher_pass_confirm
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
