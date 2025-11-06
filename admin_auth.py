# admin_auth.py — InsightFace + OpenCV integration for admin auth
import os
import cv2
import smtplib
import random
import numpy as np
import streamlit as st
from PIL import Image
from glob import glob
from email.message import EmailMessage
from insightface.app import FaceAnalysis
import csv
import datetime

# ---------------- Constants ---------------- #
ADMIN_DATA_DIR = "admin_data"
os.makedirs(ADMIN_DATA_DIR, exist_ok=True)

LOG_FILE = "face_logs.csv"  # file to log attempts

EMAIL_ADDRESS = "mpmc.projectpi@gmail.com"
EMAIL_PASSWORD = "wtlz wlaf biei gvhq"
MASTER_EMAIL = "vartamame69@gmail.com"

THRESHOLD = 0.5   # cosine similarity threshold
IND = -1           # index of matched admin in gallery

# ---------------- InsightFace Init ---------------- #
_insight_app = None
def _ensure_insight_app(cpu: bool = True, det_size=(640, 640)) -> FaceAnalysis:
    global _insight_app
    if _insight_app is None:
        _insight_app = FaceAnalysis(name="buffalo_l")
        _insight_app.prepare(ctx_id=-1 if cpu else 0, det_size=det_size)
    return _insight_app

def l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / (n + 1e-10)

# ---------------- Logging ---------------- #
def log_face_attempt(admin_name: str, similarity: float, success: bool):
    """
    Log each face recognition attempt with timestamp, admin name, similarity score, and result.
    """
    header = ["timestamp", "admin_name", "similarity", "success"]

    # Create file with header if not exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    # Append log entry
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            admin_name,
            f"{similarity:.4f}",
            "True" if success else "False"
        ])

# ---------------- OTP ---------------- #
def send_master_otp():
    otp = str(random.randint(100000, 999999))
    msg = EmailMessage()
    msg.set_content(f"Your OTP for admin verification is: {otp}")
    msg["Subject"] = "Admin Verification OTP"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = MASTER_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return otp

def send_otp():
    otp = str(random.randint(100000, 999999))
    names, centroids, emails = load_admin_gallery()
    to_email = emails[IND] if 0 <= IND < len(emails) else MASTER_EMAIL
    msg = EmailMessage()
    msg.set_content(f"Your OTP for admin verification is: {otp}")
    msg["Subject"] = "Admin Verification OTP"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return otp

def authenticate_master_admin():
    if "otp_sent" not in st.session_state:
        st.session_state.generated_otp = send_master_otp()
        st.session_state.otp_sent = True
        st.session_state.otp_verified = False
        st.info(f"OTP sent to master email: {MASTER_EMAIL}")
        return False

    with st.form(key="admin_otp_form"):
        user_otp = st.text_input("Enter OTP", type="password")
        submit = st.form_submit_button("Verify OTP")
        if submit:
            if user_otp == st.session_state.get("generated_otp", ""):
                st.session_state.otp_verified = True
                st.success("✅ OTP verified successfully.")
                return True
            else:
                st.error("❌ Invalid OTP.")
                return False
    return st.session_state.get("otp_verified", False)

def authenticate_admin():
    global IND
    if "otp_sent" not in st.session_state:
        st.session_state.generated_otp = send_otp()
        st.session_state.otp_sent = True
        st.session_state.otp_verified = False
        names, centroids, emails = load_admin_gallery()
        to_email = emails[IND] if 0 <= IND < len(emails) else MASTER_EMAIL
        st.info(f"OTP sent to: {to_email}")
        return False

    with st.form(key="admin_otp_form"):
        user_otp = st.text_input("Enter OTP", type="password")
        submit = st.form_submit_button("Verify OTP")
        if submit:
            if user_otp == st.session_state.get("generated_otp", ""):
                st.session_state.otp_verified = True
                st.success("✅ OTP verified successfully.")
                return True
            else:
                st.error("❌ Invalid OTP.")
                return False
    return st.session_state.get("otp_verified", False)

# ---------------- Face Authentication ---------------- #
def authenticate_admin_face(threshold: float = THRESHOLD, cpu: bool = True):
    """
    Captures a frame from webcam, detects faces with InsightFace, 
    computes normalized embedding, and matches against stored admin embeddings.
    Logs each attempt with similarity score and result.
    """
    global IND
    names, centroids, emails = load_admin_gallery()
    if centroids is None or len(centroids) == 0:
        st.error("❌ No registered admins found.")
        log_face_attempt("Unknown", 0.0, False)
        return False

    app = _ensure_insight_app(cpu=cpu)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    st.info("📷 Scanning face... please look at the camera.")

    if not cap.isOpened():
        st.error("❌ Could not open webcam.")
        log_face_attempt("Unknown", 0.0, False)
        return False

    # Warm-up frames
    for _ in range(15):
        cap.read()

    ret, frame_bgr = cap.read()
    cap.release()

    if not ret or frame_bgr is None:
        st.error("❌ Camera error.")
        log_face_attempt("Unknown", 0.0, False)
        return False

    faces = app.get(frame_bgr)
    if not faces:
        st.error("❌ No face detected.")
        log_face_attempt("Unknown", 0.0, False)
        return False

    # Select largest face
    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
    emb = getattr(face, "normed_embedding", None)
    if emb is None:
        emb = l2_normalize(face.embedding)

    sims = centroids @ emb
    best_idx = int(np.argmax(sims))
    best_sim = float(sims[best_idx])

    if best_sim >= threshold:
        IND = best_idx
        st.success(f"✅ Recognized as {names[best_idx]} ({best_sim:.2f})")
        log_face_attempt(names[best_idx], best_sim, True)
        return True
    else:
        st.error("❌ No matching admin. Try better lighting/angle.")
        log_face_attempt("Unknown", best_sim, False)
        return False

# ---------------- Admin Registration ---------------- #
def register_new_admin_with_face():
    st.subheader("📝 Register Admin with Face")

    name = st.text_input("Admin Name")
    email = st.text_input("Admin Email")
    if not name or not email:
        st.warning("Please enter both name and email.")
        return

    # Step 1: OTP Verification
    if not st.session_state.get("admin_registration_otp_verified"):
        if st.button("Send OTP", key="send_reg_otp"):
            st.session_state.generated_admin_otp = send_master_otp()
            st.session_state.admin_registration_otp_sent = True
            st.info("OTP sent to master email.")
        if st.session_state.get("admin_registration_otp_sent"):
            otp_input = st.text_input("Enter OTP", type="password")
            if st.button("Verify OTP", key="verify_reg_otp"):
                if otp_input == st.session_state.get("generated_admin_otp"):
                    st.session_state.admin_registration_otp_verified = True
                    st.success("✅ OTP verified.")
                else:
                    st.error("❌ Invalid OTP.")
        return

    # Step 2: Use Streamlit's camera_input instead of cv2.VideoCapture
    img_file_buffer = st.camera_input("📸 Capture Face")

    if img_file_buffer is not None:
        # Convert uploaded image to numpy array
        image = Image.open(img_file_buffer)
        image_rgb = np.array(image.convert("RGB"))
        st.image(image_rgb, caption="Captured Face", channels="RGB")

        if st.button("✅ Confirm & Register", key="confirm_register"):
            ok = save_admin_data(image_rgb, name, email)
            if ok:
                st.success("🎉 Admin registered successfully.")
                for k in [
                    "generated_admin_otp", "admin_registration_otp_sent",
                    "admin_registration_otp_verified", "captured_frame"
                ]:
                    if k in st.session_state:
                        del st.session_state[k]
            else:
                st.error("❌ No face detected in image. Try again.")


# ---------------- Helpers ---------------- #
def save_admin_data(image_rgb: np.ndarray, name: str, email: str) -> bool:
    app = _ensure_insight_app(cpu=True)

    img_path = os.path.join(ADMIN_DATA_DIR, f"{name}.jpg")
    Image.fromarray(image_rgb).save(img_path)

    email_path = os.path.join(ADMIN_DATA_DIR, f"{name}.txt")
    with open(email_path, "w") as f:
        f.write(email.strip())

    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    faces = app.get(image_bgr)
    if not faces:
        if os.path.exists(img_path): os.remove(img_path)
        if os.path.exists(email_path): os.remove(email_path)
        return False

    face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
    emb = getattr(face, "normed_embedding", None)
    if emb is None:
        emb = l2_normalize(face.embedding)

    np.save(os.path.join(ADMIN_DATA_DIR, f"{name}.npy"), emb.astype(np.float32))
    return True

def load_admin_gallery():
    app = _ensure_insight_app(cpu=True)
    names, embeddings, emails = [], [], []

    jpgs = sorted(glob(os.path.join(ADMIN_DATA_DIR, "*.jpg")))
    for img_path in jpgs:
        name = os.path.splitext(os.path.basename(img_path))[0]
        emb_path = os.path.join(ADMIN_DATA_DIR, f"{name}.npy")
        email_path = os.path.join(ADMIN_DATA_DIR, f"{name}.txt")

        email_val = MASTER_EMAIL
        if os.path.exists(email_path):
            try:
                with open(email_path, "r") as f:
                    email_val = f.read().strip()
            except Exception:
                pass

        if os.path.exists(emb_path):
            try:
                emb = np.load(emb_path)
            except Exception:
                emb = None
        else:
            img = cv2.imread(img_path)
            faces = app.get(img) if img is not None else []
            if faces:
                face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                emb = getattr(face, "normed_embedding", None)
                if emb is None:
                    emb = l2_normalize(face.embedding)
                np.save(emb_path, emb.astype(np.float32))
            else:
                emb = None

        if emb is not None:
            names.append(name)
            embeddings.append(emb)
            emails.append(email_val)

    if len(embeddings) == 0:
        return [], np.array([]), []
    centroids = np.vstack(embeddings).astype(np.float32)
    return names, centroids, emails
