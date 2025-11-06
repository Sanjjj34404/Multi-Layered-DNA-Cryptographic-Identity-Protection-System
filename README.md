# 🧬 Multi-Layered DNA Cryptographic Identity Protection System

A secure identity management system that protects patient identities using **DNA-based cryptography**, **multi-factor authentication**, and **AES-256 encryption**.  
This project integrates **biometric authentication (face recognition)**, **OTP-based temporal validation**, and a **dual-database architecture** for enhanced data security in healthcare environments.

---

## 🔐 Overview

This project is based on the research paper  
**“A Multi-Layered DNA Cryptographic Model for Securing Patient Identities.”**

It introduces a **biology-inspired cryptographic framework** that leverages genetic randomness from DNA sequences to dynamically generate encryption keys for safeguarding electronic health records (EHRs).  
The system ensures data privacy, regulatory compliance, and tamper-proof access verification.

---

## 🚀 Features

- **DNA-Based AES Encryption:**  
  Encrypts patient data using AES-256 with keys derived dynamically from DNA sequences via PBKDF2-HMAC-SHA256.

- **Multi-Factor Authentication (MFA):**  
  Combines facial recognition and one-time password (OTP) verification for admin access.

- **Dual Database Architecture:**  
  Separates encrypted medical records and DNA sequences to prevent key compromise.

- **Streamlit Web Interface:**  
  Provides a clean, interactive UI for encryption, decryption, and user authentication.

- **Security Enhancements:**  
  Protects against brute-force, replay, and impersonation attacks.

---

## 🧠 Tech Stack

| Category | Technologies |
|-----------|---------------|
| **Frontend** | Streamlit |
| **Backend** | Python (Flask/Streamlit) |
| **Database** | MySQL |
| **Encryption** | AES-256, PBKDF2-HMAC-SHA256 |
| **Authentication** | Face Recognition, OTP (via Email) |
| **Cryptography Concept** | DNA Sequence Encoding |
| **Language** | Python 3.10+ |

---

## 🧩 System Architecture
User → Face Recognition → OTP Validation → DNA Key Generation → AES-256 Encryption/Decryption → MySQL Database
