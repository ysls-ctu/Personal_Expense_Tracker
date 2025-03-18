import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import pyrebase
import pandas as pd
import datetime
import time
import json

# Load Firebase Admin SDK (for Firestore)
if not firebase_admin._apps:
    cred = credentials.Certificate("expense-tracker-9deb0-firebase-adminsdk-fbsvc-a24c7b4c6a.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Load Firebase config (for Authentication)
def init_firebase():
    with open("firebase-config.json") as f:
        firebase_config = json.load(f)
    return pyrebase.initialize_app(firebase_config)

firebase = init_firebase()
auth_client = firebase.auth()

st.set_page_config(page_title="Personal Expense Tracker", page_icon="💸", layout="centered")

# UI Styling
st.markdown(
    """
    <style>

        .title {
            font-size: 35px;
            font-weight: 900 !important;
            margin-bottom: 15px;

            text-align: center;
        }
        .input-box {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 8px;
        }
        .btn {
            width: 100%;
            padding: 10px;
            font-size: 1rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: 0.3s;
        }
        .btn-primary { background: red; color: white; }
        .btn-primary:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; color: white; margin-top: 10px; }
        .btn-secondary:hover { background: #545b62; }

    </style>
    """,
    unsafe_allow_html=True,
)

def to_login():
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown('<div class="title">Login</div>', unsafe_allow_html=True)
    email = st.text_input("Enter your registered email", placeholder="")
    password = st.text_input("Enter your password", placeholder="", type="password")
    st.markdown('<br>', unsafe_allow_html=True)

    login_btn = st.button("Login", key="login", use_container_width=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown('<center><p>or</p></center>', unsafe_allow_html=True)
        signup_btn = st.button("Don't have an account? Create account", key="signup", use_container_width=True)

    if login_btn:
        try:
            user = auth_client.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
            st.success("✅ Logged in successfully! Redirecting...")
            time.sleep(2)
            st.session_state["page"] = "Dashboard"
            st.rerun()
        except Exception as e:
            st.error("❌ Invalid credentials. Please try again.")

    if signup_btn:
        st.session_state["page"] = "Sign Up"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def to_signup():
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown('<div class="title">Create an Account</div>', unsafe_allow_html=True)

    email = st.text_input("Enter your email", placeholder="")
    confirm_email = st.text_input("Confirm your email", placeholder="")
    password = st.text_input("Enter your password", placeholder="", type="password")
    confirm_password = st.text_input("Confirm your password", placeholder="", type="password")
    st.markdown('<br>', unsafe_allow_html=True)

    if (email == confirm_email) and (password == confirm_password):
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            try:
                auth_client.create_user_with_email_and_password(email, password)
                st.success("✅ Account created successfully! Please log in.")
                time.sleep(2)
                st.session_state["page"] = "Login"
                st.rerun()
            except Exception as e:
                error_message = str(e)
                if "EMAIL_EXISTS" in error_message:
                    st.error("⚠️ This email is already registered. Please log in.")
                    time.sleep(2)
                    st.session_state["page"] = "Login"
                    st.rerun()
                else:
                    st.error(f"❌ Error: {error_message}")
    elif (email != confirm_email) and (password == confirm_password):
        st.error("⚠️ Email address entered does not match!")
    elif (email == confirm_email) and (password != confirm_password):
        st.error("⚠️ Password entered does not match!")
    elif (email != confirm_email) and (password != confirm_password):
        st.error("⚠️ Email address and Password does not match")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown('<center><p>or</p></center>', unsafe_allow_html=True)
        back_login_btn = st.button("Already got an account? Login", key="signup", use_container_width=True)

    if back_login_btn:
        st.session_state["page"] = "Login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def to_dashboard():
    if "user" in st.session_state:
        user = st.session_state["user"]
        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown('<div class="title">📊 Dashboard</div>', unsafe_allow_html=True)

        amount = st.number_input("💸 Expense Amount", min_value=0.01)
        category = st.selectbox("📂 Category", ["Food", "Transport", "Shopping", "Other"])
        date = st.date_input("📅 Date", datetime.date.today())

        if st.button("➕ Add Expense"):
            try:
                db.collection("expenses").add({
                    "user": user["email"],
                    "amount": amount,
                    "category": category,
                    "date": date.strftime("%Y-%m-%d")
                })
                st.success("✅ Expense added successfully!")
            except Exception as e:
                st.error(f"❌ Error adding expense: {e}")

        st.subheader("📜 Your Expenses")
        try:
            docs = db.collection("expenses").where("user", "==", user["email"]).stream()
            expenses = [{**doc.to_dict(), "id": doc.id} for doc in docs]

            if expenses:
                df = pd.DataFrame(expenses)
                st.dataframe(df)
            else:
                st.info("ℹ️ No expenses recorded yet.")
        except Exception as e:
            st.error(f"❌ Error fetching expenses: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.session_state["page"] = "Login"
            st.rerun()
    else:
        st.warning("⚠️ Please log in to access the dashboard.")

col1, col_image, col3 = st.columns([1, 5, 1])
with col_image:
    st.image("header_bg.png", width=1000)

# Sidebar Menu
menu = ["Login", "Sign Up", "Dashboard"]
if "page" not in st.session_state:
    st.session_state["page"] = "Login"

if st.session_state["page"] == "Login":
    to_login()
elif st.session_state["page"] == "Sign Up":
    to_signup()
elif st.session_state["page"] == "Dashboard":
    to_dashboard()
