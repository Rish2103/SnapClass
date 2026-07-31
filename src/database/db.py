from src.database.config import supabase

import bcrypt

def hash_pass(password):
    #Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')

def check_password(password, hashed_password):
    #Check if the password matches the hashed password
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def check_teacher_exists(username):
    #CHeck for unique username in the database
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    return len(response.data) > 0

def validate_password_strength(password):
    """
    Validate password meets minimum security requirements.
    Returns (is_valid: bool, message: str).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

def create_teacher(username, name, password, security_question=None, security_answer=None, email=None):
    data = {
        "username": username,
        "name": name,
        "password": hash_pass(password),
    }
    if email:
        data["email"] = email.strip().lower()
    if security_question and security_answer:
        data["security_question"] = security_question
        data["security_answer"] = hash_pass(security_answer.strip().lower())
    #Insert the new teacher into the database
    response = supabase.table("teachers").insert(data).execute()
    return response.data

def get_teacher_by_username(username):
    """Fetch a teacher record by username. Returns the teacher dict or None."""
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        return response.data[0]
    return None

def get_teacher_by_email(email):
    """Fetch a teacher record by email. Returns the teacher dict or None."""
    response = supabase.table("teachers").select("*").eq("email", email.strip().lower()).execute()
    if response.data:
        return response.data[0]
    return None

def verify_security_answer(username, answer):
    """
    Verify the security answer for a teacher's forgot password flow.
    Returns (is_valid: bool, teacher: dict or None).
    """
    teacher = get_teacher_by_username(username)
    if not teacher:
        return False, None
    stored_hash = teacher.get("security_answer")
    if not stored_hash:
        return False, None
    is_correct = check_password(answer.strip().lower(), stored_hash)
    if is_correct:
        return True, teacher
    return False, None

def update_teacher_password(teacher_id, new_password):
    """Update a teacher's password (hashed with bcrypt)."""
    hashed = hash_pass(new_password)
    response = supabase.table("teachers").update({"password": hashed}).eq("teacher_id", teacher_id).execute()
    return response.data

def teacher_login(username, password):
    #Check if the teacher exists in the database
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_password(password, teacher["password"]):
            return teacher
    #Check if the password matches
    
    return None

def get_all_students():
    #Get all students from the database
    response = supabase.table("students").select("*").execute()
    return response.data

def create_student(new_name,face_embedding,voice_embedding):
    data = {'name':new_name, 'face_embedding':face_embedding,'voice_embedding':voice_embedding}
    response = supabase.table('students').insert(data).execute()
    return response.data

def update_student_face_embedding(student_id, face_embedding):
    """Update face_embedding for an existing student by student_id."""
    try:
        sid = int(student_id)
    except (ValueError, TypeError):
        sid = student_id
    try:
        response = supabase.table('students').update({'face_embedding': face_embedding}).eq('student_id', sid).execute()
        return response.data
    except Exception as e:
        print(f"Supabase UPDATE table 'students' error: {e}")
        return None

def create_subject(subject_code,name,section,teacher_id):
    data ={'subject_code' : subject_code, 'name' : name, 'section' : section, 'teacher_id' : teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data

def check_subject_exists(subject_code, teacher_id):
    """Check if a subject with the same code already exists for this teacher"""
    response = supabase.table("subjects").select("*").eq("subject_code", subject_code).eq("teacher_id", teacher_id).execute()
    return len(response.data) > 0

def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select('*,subject_students(count),attendance_logs(timestamp)').eq('teacher_id',teacher_id).execute()
    subjects = response.data
    
    for sub in subjects:
        sub['total_students'] = sub.get("subject_students",[{}])[0].get('count',0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs',[])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
        sub['total_classes'] = unique_sessions
        
        sub.pop('subject_students',None)
        sub.pop('attendance_logs',None)
        
    return subjects
def enroll_student_to_subject(student_id,subject_id):
    data = {'student_id' : student_id, 'subject_id' : subject_id}
    respone = supabase.table('subject_students').insert(data).execute()
    return respone.data

def unenroll_student_to_subject(student_id,subject_id):
    data = {'student_id' : student_id, 'subject_id' : subject_id}
    respone = supabase.table('subject_students').delete().eq('student_id',student_id).eq('subject_id',subject_id).execute()
    return respone.data

def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*,subjects(*)').eq('student_id',student_id).execute()
    return response.data
    
def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*,subjects(*)').eq('student_id',student_id).execute()
    return response.data

def create_attendance(logs):
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data

def get_attendance_for_teacher(teacher_id):
    response = supabase.table('attendance_logs').select('*,subjects!inner(*)').eq('subjects.teacher_id', teacher_id).execute()
    return response.data