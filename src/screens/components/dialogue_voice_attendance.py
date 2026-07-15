from datetime import datetime

import streamlit as st
import pandas as pd

from src.pipelines.voice_pipeline import process_bulk_audio
from src.database.config import supabase

from src.screens.components.dialogue_attendance_results import show_attendance_results


@st.dialog("Voice Attendance")
def voice_attendance_logs(selected_subject_id):
    st.write(
        "Record audio of students saying I am present. Then AI will recognize the students."
    )

    audio_data = None

    audio_data = st.audio_input("Record classroom audio")

    if st.button("Analyze Audio", width="stretch", type="primary"):
        if audio_data is None:
            st.error("Please record audio first!")
            return
        
        with st.spinner("Processing audio data"):
            enrolled_res = (
                supabase.table("subject_students")
                .select("*,students(*)")
                .eq("subject_id", selected_subject_id)
                .execute()
            )
            enrolled_students = enrolled_res.data

            if not enrolled_students:
                st.warning("No students enrolled in this course!")
                return
            candidates_dict = {
                s["students"]["student_id"]: s["students"]["voice_embedding"]
                for s in enrolled_students
                if s["students"].get("voice_embedding")
            }
            if not candidates_dict:
                st.error("No enrolled students have voice profiles registered")

            audio_bytes = audio_data.read()

            detected_scores = process_bulk_audio(audio_bytes, candidates_dict)

            results, attendance_to_log = [], []

            current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            for node in enrolled_students:
                student = node["students"]
                scores = detected_scores.get(int(student["student_id"]), 0.0)
                is_present = bool(scores > 0)

                results.append(
                    {
                        "Name": student["name"],
                        "ID": student["student_id"],
                        "Source": scores if is_present else "-",
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

            st.session_state.voice_attendance_results = (
                pd.DataFrame(results),
                attendance_to_log,
            )

    if st.session_state.get("voice_attendance_results"):
        st.divider()
        df_results, logs = st.session_state.voice_attendance_results
        show_attendance_results(df_results,logs)
