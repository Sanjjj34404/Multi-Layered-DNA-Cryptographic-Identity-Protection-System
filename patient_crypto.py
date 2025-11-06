import mysql.connector
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import datetime
#import face_recognition
import numpy as np
import smtplib
from email.message import EmailMessage
import random
from PIL import Image

# ------------------- CONSTANTS ------------------- #
MASTER_KEY = b"kJ7@p9$Z1wQx%V8nE4mT&h2!Lr3Yf6#B"  # fixed master key for DNA encryption

# ------------------- ENCRYPTION UTILS ------------------- #
def derive_key(dna_sequence: str) -> bytes:
    salt = b'static_salt_123'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(dna_sequence.encode())

def encrypt_with_key(data: str, key: bytes) -> str:
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode()

def decrypt_with_key(encrypted_data: str, key: bytes) -> str:
    raw = base64.b64decode(encrypted_data)
    iv = raw[:16]
    encrypted = raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode()

# ------------------- DATABASE UTILS ------------------- #
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="patient"
    )

def store_patient_data(patient_id, full_name, email, contact_number, dob, gender, address, dna_sequence):
    # Step 1: encrypt DNA using master key
    dna_encrypted = encrypt_with_key(dna_sequence, MASTER_KEY)

    # Step 2: derive patient-specific key from original DNA
    key = derive_key(dna_sequence)
    now = datetime.datetime.now()

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM sequence WHERE patient_id = %s", (patient_id,))
        if cursor.fetchone():
            raise ValueError("❌ Patient ID already exists. Please use a different one.")

        encrypted_data = {
            "patient_id": patient_id,
            "full_name": encrypt_with_key(full_name, key),
            "email": encrypt_with_key(email, key),
            "contact_number": encrypt_with_key(contact_number, key),
            "dob": encrypt_with_key(dob, key),
            "gender": encrypt_with_key(gender, key),
            "address": encrypt_with_key(address, key),
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Store encrypted patient data
        cursor.execute("""
            INSERT INTO patient_data (patient_id, full_name, email, contact_number, dob, gender, address, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuple(encrypted_data.values()))

        # Store encrypted DNA (not plaintext anymore)
        cursor.execute("""
            INSERT INTO sequence (patient_id, dna_sequence)
            VALUES (%s, %s)
        """, (patient_id, dna_encrypted))

        conn.commit()
        return True

    finally:
        conn.close()

def retrieve_and_decrypt(patient_id):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT dna_sequence FROM sequence WHERE patient_id = %s", (patient_id,))
        result = cursor.fetchone()
        if not result:
            return None

        # Step 1: decrypt DNA using master key
        dna_sequence = decrypt_with_key(result[0], MASTER_KEY)

        # Step 2: derive patient-specific key
        key = derive_key(dna_sequence)

        cursor.execute("SELECT * FROM patient_data WHERE patient_id = %s", (patient_id,))
        row = cursor.fetchone()
        if not row:
            return None

        decrypted_data = {
            "patient_id": patient_id,
            "full_name": decrypt_with_key(row[1], key),
            "email": decrypt_with_key(row[2], key),
            "contact_number": decrypt_with_key(row[3], key),
            "dob": decrypt_with_key(row[4], key),
            "gender": decrypt_with_key(row[5], key),
            "address": decrypt_with_key(row[6], key),
            "created_at": row[7],
            "updated_at": row[8]
        }

        return decrypted_data

    finally:
        conn.close()

# ------------------- DELETE RECORD ------------------- #
def delete_patient_record(patient_id: str) -> bool:
    """
    Deletes a patient record from both patient_data and sequence tables by patient_id.
    
    Args:
        patient_id (str): The unique ID of the patient to delete.

    Returns:
        bool: True if deleted successfully, False if no record found.
    """
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Check if patient exists
        cursor.execute("SELECT 1 FROM patient_data WHERE patient_id = %s", (patient_id,))
        if not cursor.fetchone():
            return False

        # Delete from both tables
        cursor.execute("DELETE FROM patient_data WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM sequence WHERE patient_id = %s", (patient_id,))
        conn.commit()
        return True

    except Exception as e:
        print(f"Error deleting patient record: {e}")
        return False

    finally:
        conn.close()
