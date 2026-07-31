import numpy as np
import streamlit as st


from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from src.database.db import get_all_students


@st.cache_resource
def load_dlib_models():
    try:
        import dlib
        import face_recognition_models
    except Exception as e:
        st.error(
            "Face recognition models unavailable in this environment: {}".format(e)
        )
        return None, None, None

    detector = dlib.get_frontal_face_detector()

    sp = dlib.shape_predictor(face_recognition_models.pose_predictor_model_location())

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec


def get_face_embedding(image_np):
    detector, sp, facerec = load_dlib_models()

    # If native face models couldn't be loaded, return empty embeddings
    if detector is None or sp is None or facerec is None:
        return []

    faces = detector(image_np, 1)

    encodings = []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(
            image_np, shape, 1
        )  # 123 embedding

        encodings.append(np.array(face_descriptor))
    return encodings


@st.cache_resource
def get_trained_model():
    X = []
    y = []

    student_db = get_all_students()

    if not student_db:
        st.warning(
            "⚠️ No students found in database. Check Supabase RLS policies.", icon="🔒"
        )
        return None

    for student in student_db:
        embedding = student.get("face_embedding")
        student_id = (
            student.get("student_id")
            if student.get("student_id") is not None
            else student.get("id")
        )
        if embedding and student_id is not None:
            X.append(np.array(embedding))
            y.append(student_id)

    if len(X) == 0:
        st.warning(
            "⚠️ No valid face embeddings found. Ensure students have registered faces.",
            icon="📸",
        )
        return None

    # Use CalibratedClassifierCV to avoid the deprecated `probability=True` on SVC.
    base_svc = SVC(kernel="linear", class_weight="balanced")
    clf = CalibratedClassifierCV(base_svc, cv=3)

    try:
        clf.fit(X, y)
    except ValueError:
        pass

    return {"clf": clf, "X": X, "y": y}


def train_classifier():
    st.cache_resource.clear()
    model_data = get_trained_model()

    return bool(model_data)


def compute_eye_aspect_ratio(shape):
    """
    Compute the Eye Aspect Ratio (EAR) from dlib 68-point landmarks.
    Uses landmarks 36-41 (left eye) and 42-47 (right eye).

    EAR = (||p1-p5|| + ||p2-p4||) / (2 * ||p0-p3||)

    Open eyes: EAR ≈ 0.20 - 0.35
    Closed eyes: EAR ≈ 0.02 - 0.15

    Returns the average EAR across both eyes.
    """
    pts = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)], dtype=np.float64)

    # Left eye: landmarks 36-41
    left_eye = pts[36:42]
    # Right eye: landmarks 42-47
    right_eye = pts[42:48]

    def _ear(eye):
        # Vertical distances
        v1 = np.linalg.norm(eye[1] - eye[5])
        v2 = np.linalg.norm(eye[2] - eye[4])
        # Horizontal distance
        h = np.linalg.norm(eye[0] - eye[3])
        if h < 1e-5:
            return 0.0
        return (v1 + v2) / (2.0 * h)

    left_ear = _ear(left_eye)
    right_ear = _ear(right_eye)
    return (left_ear + right_ear) / 2.0


def verify_blink_liveness(img_open, img_closed):
    """
    Two-step blink-based liveness verification.

    Takes two images: one with eyes open, one with eyes closed.
    Verifies:
      1. A face is detected in both images
      2. The EAR dropped significantly between open→closed (proving a real blink)
      3. The face encoding matches between both images (same person)

    A static photo on a phone screen cannot close its eyes, so the EAR
    will remain the same across both captures → spoof detected.

    Returns: (is_live: bool, reason: str, details: dict)
    """
    detector, sp, facerec = load_dlib_models()

    if detector is None or sp is None or facerec is None:
        return False, "Face models unavailable", {}

    # --- Detect face in eyes-open image ---
    faces_open = detector(img_open, 1)
    if len(faces_open) == 0:
        return False, "No face detected in eyes-open photo", {}
    if len(faces_open) > 1:
        return False, "Multiple faces in eyes-open photo", {}

    shape_open = sp(img_open, faces_open[0])
    ear_open = compute_eye_aspect_ratio(shape_open)

    # Get face encoding from eyes-open image
    desc_open = facerec.compute_face_descriptor(img_open, shape_open, 1)
    encoding_open = np.array(desc_open)

    # --- Detect face in eyes-closed image ---
    faces_closed = detector(img_closed, 1)
    if len(faces_closed) == 0:
        return False, "No face detected in eyes-closed photo. Make sure your face is visible even with eyes closed.", {}
    if len(faces_closed) > 1:
        return False, "Multiple faces in eyes-closed photo", {}

    shape_closed = sp(img_closed, faces_closed[0])
    ear_closed = compute_eye_aspect_ratio(shape_closed)

    # Get face encoding from eyes-closed image
    desc_closed = facerec.compute_face_descriptor(img_closed, shape_closed, 1)
    encoding_closed = np.array(desc_closed)

    # --- Check 1: Same person across both photos ---
    face_distance = np.linalg.norm(encoding_open - encoding_closed)
    if face_distance > 0.6:
        return False, "Face mismatch: the two photos appear to be different people", {
            "ear_open": float(ear_open),
            "ear_closed": float(ear_closed),
            "face_distance": float(face_distance),
        }

    # --- Check 2: EAR drop (eyes actually closed in second photo) ---
    ear_drop = ear_open - ear_closed
    relative_drop = ear_drop / (ear_open + 1e-6)

    details = {
        "ear_open": float(ear_open),
        "ear_closed": float(ear_closed),
        "ear_drop": float(ear_drop),
        "relative_drop": float(relative_drop),
        "face_distance": float(face_distance),
    }

    # A real blink or eye closure produces relative_drop >= 0.18 OR ear_drop >= 0.035.
    # Static phone photos present identical frames with relative_drop < 0.08.
    if relative_drop < 0.18 and ear_drop < 0.035:
        return False, "No significant eye state change detected between the two photos. Please close your eyes fully in step 2.", details

    return True, "Liveness verified", details


from PIL import Image, ImageDraw, ImageFont


def check_duplicate_face(new_encoding_np, resemblance_threshold=0.50):
    """
    Check if a face encoding is already registered under an existing student.
    Returns (is_duplicate: bool, existing_student_name: str or None).
    """
    all_students = get_all_students()
    if not all_students:
        return False, None

    for student in all_students:
        embedding = student.get("face_embedding")
        if embedding:
            existing_emb = np.array(embedding)
            dist = np.linalg.norm(existing_emb - new_encoding_np)
            if dist < resemblance_threshold:
                return True, student.get("name", "Unknown Student")

    return False, None


def predict_attendance(class_image_np):
    """
    Detect and identify students in a class image.
    Returns: (detected_student: dict, all_students: list, num_faces: int, annotated_img_np: np.ndarray)
    """
    detector, sp, facerec = load_dlib_models()
    detected_student = {}
    annotated_img = Image.fromarray(class_image_np.copy())
    draw = ImageDraw.Draw(annotated_img)

    if detector is None or sp is None or facerec is None:
        return detected_student, [], 0, class_image_np

    faces = detector(class_image_np, 1)

    if not faces:
        return detected_student, [], 0, class_image_np

    model_data = get_trained_model()
    all_student_records = get_all_students() or []
    student_name_map = {
        s.get("student_id") if s.get("student_id") is not None else s.get("id"): s.get("name", "Student")
        for s in all_student_records
    }

    if not model_data:
        # Draw yellow boxes for all detected faces if model not trained yet
        w_img, h_img = annotated_img.size
        for face in faces:
            left, top, right, bottom = face.left(), face.top(), face.right(), face.bottom()
            draw.rectangle([left, top, right, bottom], outline="#F39C12", width=3)
            draw.rectangle([left, max(0, top - 24), left + 120, top], fill="#F39C12")
            draw.text((left + 5, max(0, top - 20)), "Face Detected", fill="white")
        return detected_student, [], len(faces), np.array(annotated_img)

    clf = model_data["clf"]
    X_train = model_data["X"]
    y_train = model_data["y"]

    all_students = sorted([sid for sid in set(y_train) if sid is not None])

    for face in faces:
        shape = sp(class_image_np, face)
        left, top, right, bottom = max(0, face.left()), max(0, face.top()), min(class_image_np.shape[1], face.right()), min(class_image_np.shape[0], face.bottom())

        face_descriptor = facerec.compute_face_descriptor(
            class_image_np, shape, 1
        )
        encoding = np.array(face_descriptor)

        is_recognized = False
        matched_name = "Unregistered"

        if all_students:
            if len(all_students) >= 2:
                predicted_id = clf.predict([encoding])[0]
            else:
                predicted_id = all_students[0]

            if predicted_id is not None:
                student_embedding = X_train[y_train.index(predicted_id)]
                best_match_score = np.linalg.norm(student_embedding - encoding)

                resemblance_threshold = 0.60

                if best_match_score <= resemblance_threshold:
                    detected_student[predicted_id] = True
                    is_recognized = True
                    matched_name = student_name_map.get(predicted_id, f"Student {predicted_id}")

        # Draw bounding box & label overlay
        if is_recognized:
            box_color = "#2ECC71"  # Vibrant Emerald Green
            label_text = f"  {matched_name}  "
        else:
            box_color = "#E74C3C"  # Crimson Red
            label_text = "  Unregistered  "

        draw.rectangle([left, top, right, bottom], outline=box_color, width=4)
        label_top = max(0, top - 26)
        label_width = len(label_text) * 8 + 10
        draw.rectangle([left, label_top, left + label_width, top], fill=box_color)
        draw.text((left + 4, label_top + 4), label_text, fill="white")

    return detected_student, all_students, len(faces), np.array(annotated_img)





