import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import pyrebase
import pandas as pd
import datetime
import time
import json
import re
from PIL import Image
import io
from datetime import date, timedelta

# Load Firebase Admin SDK 
if not firebase_admin._apps:
    cred = credentials.Certificate("expense-tracker-9deb0-firebase-adminsdk-fbsvc-a24c7b4c6a.json")
    firebase_admin.initialize_app(cred, {"storageBucket": "expense-tracker-9deb0.appspot.com"}) 

db = firestore.client()

# Load Firebase config 
def init_firebase():
    with open("firebase-config.json") as f:
        firebase_config = json.load(f)
    return pyrebase.initialize_app(firebase_config)

firebase = init_firebase()
auth_client = firebase.auth()

st.set_page_config(page_title="Personal Expense Tracker", page_icon="📊", layout="centered")

# UI Styling
st.markdown(
    """
    <style>

        .title {
            font-size: 35px;
            font-weight: 900 !important;
            margin-bottom: 15px;
            text-align: center;
            line-height: 0.9;
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
        hr.style-two-grid {
            border: 0;
            height: 5px !important;
            background: #333;
            background-image: linear-gradient(to right, #ccc, black, #ccc);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

def to_login():
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
    st.markdown('<div class="title">Login</div>', unsafe_allow_html=True)
    email = st.text_input("Enter your registered email", placeholder="")
    password = st.text_input("Enter your password", placeholder="", type="password")
    st.markdown('<br>', unsafe_allow_html=True)

    login_btn = st.button("Login", key="login", use_container_width=True)
    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

    if login_btn:
        try:
            user = auth_client.sign_in_with_email_and_password(email, password)
            user_info = auth_client.get_account_info(user['idToken'])
            email_verified = user_info['users'][0]['emailVerified']
            user_id = user_info['users'][0]['localId']  # Retrieve user ID
            if email_verified:
                # Fetch user data from Firestore
                user_doc = db.collection("users").document(user_id).get()
                if user_doc.exists:
                    st.session_state["user"] = user_doc.to_dict()  # Store user data in session
                    st.success("✅ Logged in successfully! Redirecting...")
                    time.sleep(2)
                    st.session_state["page"] = "Dashboard"
                    st.rerun()
                else:
                    st.error("❌ User data not found. Please contact support.")
            else:
                st.error("⚠️ Please verify your email before logging in. Check your inbox.")
        except Exception as e:
            st.error("❌ Invalid credentials. Please try again.")

    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    with col2:
        signup_btn = st.button("Don't have an account? \n\nCreate account", key="signup", use_container_width=True)

    with col3:
        forgot_pass_btn = st.button("Forgot your password? \n\nReset password", key="forgot_password", use_container_width=True)

    if forgot_pass_btn:
        st.session_state["page"] = "Forgot Password"
        st.rerun()

    if signup_btn:
        st.session_state["page"] = "Sign Up"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def to_signup():
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
    st.markdown('<div class="title">Create an Account</div>', unsafe_allow_html=True)

    # Name Fields
    first_name = st.text_input("First Name", key="first_name").strip()
    middle_name = st.text_input("Middle Name (Optional)", key="middle_name").strip()
    last_name = st.text_input("Last Name", key="last_name").strip()

    # Email Fields
    email = st.text_input("Enter your email", key="email").strip()
    confirm_email = st.text_input("Confirm your email", key="confirm_email").strip()
    
    # Password Fields
    password = st.text_input("Enter your password", type="password", key="password").strip()
    confirm_password = st.text_input("Confirm your password", type="password", key="confirm_password").strip()

    # Mobile Number
    country_codes = ["+1", "+44", "+61", "+91", "+63", "+81", "+86"]  
    country_code = st.selectbox("Country Code", country_codes, key="country_code")
    mobile_number = st.text_input("Mobile Number", key="mobile_number").strip()

    # Address Field
    address = st.text_area("Enter your address (House No., Street, City, State, Zip Code, Country)", key="address").strip()

    today = date.today()
    min_birthday = today - timedelta(days=365 * 100)
    max_birthday = today

    birthday = st.date_input(
        "Date of Birth",
        key="birthday",
        min_value=min_birthday,
        max_value=max_birthday,
        value=min_birthday  
    )
    uploaded_file = st.file_uploader("Upload personal picture", type=["png", "jpg", "jpeg"])
    gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"], key="gender")

    # Security Questions
    security_questions = [
        "What is your mother's maiden name?",
        "What was the name of your grade 1 teacher?",
        "What is the name of the town where you were born?",
        "What was your childhood nickname?",
        "What is your favorite book?",
        "Who are you?"
    ]
    
    selected_questions = []
    question1 = st.selectbox("Security Question 1", security_questions, key="question1")
    answer1 = st.text_input("Answer 1", type="password", key="answer1").strip()
    selected_questions.append(question1)
    question2 = st.selectbox("Security Question 2", [q for q in security_questions if q not in selected_questions], key="question2")
    answer2 = st.text_input("Answer 2", type="password", key="answer2").strip()
    selected_questions.append(question2)
    question3 = st.selectbox("Security Question 3", [q for q in security_questions if q not in selected_questions], key="question3")
    answer3 = st.text_input("Answer 3", type="password", key="answer3").strip()

    # Form validation
    if not first_name or not last_name or not re.match(r'^[A-Za-z ]+$', first_name) or not re.match(r'^[A-Za-z ]+$', last_name):
        st.error("⚠️ First and Last Name are required and must only contain letters and spaces.")
    elif email != confirm_email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        st.error("⚠️ Email addresses must match and be in a valid format.")
    elif len(password) < 10 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password) or not re.search(r'[!@#$%^&*]', password):
        st.error("⚠️ Password must be at least 10 characters long and include an uppercase letter, lowercase letter, number, and special character.")
    elif password != confirm_password:
        st.error("⚠️ Passwords do not match!")
    elif not address:
        st.error("⚠️ Address field is required.")
    elif not mobile_number or not mobile_number.isdigit():
        st.error("⚠️ Mobile number must be numeric.")
    elif gender == "Select":
        st.error("⚠️ Please select a gender.")
    else:
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            try:
                # Create user in Firebase Authentication
                user = auth_client.create_user_with_email_and_password(email, password)
                auth_client.send_email_verification(user['idToken'])
                user_id = user['localId']  # Unique ID of the user in Firebase Authentication

                image_url = None
                if uploaded_file is not None:
                    # Convert image to bytes
                    image = Image.open(uploaded_file)
                    image_bytes = io.BytesIO()
                    image.save(image_bytes, format="PNG")  # Convert to PNG format
                    image_bytes.seek(0)

                    # Upload to Firebase Storage
                    bucket = storage.bucket()
                    blob = bucket.blob(f"profile_pictures/{user_id}.png")  # Unique path for each user
                    blob.upload_from_file(image_bytes, content_type="image/png")
                    blob.make_public()  # Make image publicly accessible
                    image_url = blob.public_url  # Get the public URL
                
                # Store user data in Firestore
                user_data = {
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "mobile_number": country_code + mobile_number,
                    "address": address,
                    "birthday": str(birthday),
                    "gender": gender,
                    "security_questions": {
                        "q1": question1,
                        "a1": answer1,
                        "q2": question2,
                        "a2": answer2,
                        "q3": question3,
                        "a3": answer3,
                    },
                    "profile_picture": image_url,
                    "created_at": firestore.SERVER_TIMESTAMP,  # Timestamp for when the account was created
                }

                db.collection("users").document(user_id).set(user_data)  # Store user in Firestore

                st.success("✅ Account created successfully! Please check your email for a verification link before logging in.")
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

    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        back_login_btn = st.button("Already got an account? \n\nBack to login", key="signup_back", use_container_width=True)
    if back_login_btn:
        st.session_state["page"] = "Login"
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def to_forgot_password():
    st.markdown('<div class="title">Forgot Password</div>', unsafe_allow_html=True)

    email = st.text_input("Enter your registered email", placeholder="")

    if st.button("Send Reset Email", key="reset_password", use_container_width=True):
        try:
            auth_client.send_password_reset_email(email)
            st.success(f"✅ A password reset link has been sent to {email}. Check your inbox.")
        except Exception as e:
            st.error("❌ Error sending reset email. Please try again.")

    st.markdown('<hr>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        back_btn = st.button("Changed your mind? \n\nBack to Login", key="back_login", use_container_width=True)

    if back_btn:
        st.session_state["page"] = "Login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def to_dashboard():
    if "user" in st.session_state:
        user = st.session_state["user"]
        
        try:
            user_query = db.collection("users").where("email", "==", user["email"]).limit(1).stream()
            user_data = next(user_query, None)
            first_name = user_data.to_dict().get("first_name", "User") if user_data else "User"
        except Exception as e:
            st.error(f"❌ Error fetching user data: {e}")
            first_name = "User"

        st.markdown('<div class="container">', unsafe_allow_html=True)
        
        st.markdown(f'<div class="title">Hello, {first_name}!</div>', unsafe_allow_html=True)
        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        col1, col2 = st.columns([1,1])
        with col1:
            st.image(user_data["profile_picture"], caption="Profile Picture", use_column_width=True)

        with col2:
            st.image("header_bg.png", width=1000)

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        # Expense Input Form
        col1, col2 = st.columns([1, 1])
        with col1:
            date = st.date_input("Purchase Date", datetime.date.today())
            amount = st.number_input("Item Amount (₱)", min_value=0.01)

        with col2:
            item_name = st.text_input("Item Name", placeholder="Enter item name").strip()
            category = st.selectbox("Item Category", [
                "Grocery", "Eat Out", "Transportation", "Entertainment", "Donation", "Education", 
                "Personal Care", "Health & Wellness", "Bills & Utilities", "Travel", "Subscription", 
                "Debt Payment", "Others"
            ])

        notes = st.text_area("Notes (Optional)", key="notes").strip()

        st.markdown('<br>', unsafe_allow_html=True)
        
        # **Ensure Required Fields Are Filled**
        if st.button("Add Expense", use_container_width=True):
            if not item_name:
                st.warning("⚠️ Please enter an item name.")
            elif not category:
                st.warning("⚠️ Please select a category.")
            else:
                try:
                    db.collection("expenses").add({
                        "user": user["email"],
                        "date": date.strftime("%Y-%m-%d"),
                        "amount": amount,
                        "item_name": item_name,
                        "category": category,
                        "notes": notes  
                    })
                    st.success("✅ Expense added successfully!")
                except Exception as e:
                    st.error(f"❌ Error adding expense: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        st.subheader("Your Expenses")
        try:
            docs = db.collection("expenses").where("user", "==", user["email"]).stream()
            expenses = [{**doc.to_dict(), "id": doc.id} for doc in docs]

            if expenses:
                # Create DataFrame
                df = pd.DataFrame(expenses)

                # Rename Columns for Better Readability
                column_mapping = {
                    "date": "Purchase Date",
                    "item_name": "Item Name",
                    "amount": "Amount (₱)",
                    "category": "Category",
                    "notes": "Notes"
                }
                df.rename(columns=column_mapping, inplace=True)

                # Define Column Order
                df = df[list(column_mapping.values())]

                # Display Table with Fixed Size and Scrollbar
                st.data_editor(
                    df,
                    height=400,  # Fixed table height (adjust as needed)
                    width=700,   # Fixed table width (adjust as needed)
                    use_container_width=False,
                    hide_index=True
                )
            else:
                st.info("ℹ️ No expenses recorded yet.")
        except Exception as e:
            st.error(f"❌ Error fetching expenses: {e}")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        # **Logout Button**
        if st.button("Logout", use_container_width=True):
            st.session_state.pop("user", None)
            st.session_state["page"] = "Login"
            st.rerun()
    else:
        st.warning("⚠️ Please log in to access the dashboard.")

col1, col_image, col3 = st.columns([1, 5, 1])
with col_image:
    st.image("header_bg.png", width=1000)

# Sidebar Menu
menu = ["Login", "Sign Up", "Forgot Password", "Dashboard"]
if "page" not in st.session_state:
    st.session_state["page"] = "Login"

if st.session_state["page"] == "Login":
    to_login()
elif st.session_state["page"] == "Sign Up":
    to_signup()
elif st.session_state["page"] == "Forgot Password":
    to_forgot_password()
elif st.session_state["page"] == "Dashboard":
    to_dashboard()
