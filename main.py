import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase
import pandas as pd
from datetime import datetime, date, timedelta
import time
import json
import re
from PIL import Image, ExifTags
import io
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
from google.cloud.firestore import SERVER_TIMESTAMP
import streamlit.components.v1 as components

# check 1
if not firebase_admin._apps:
    firebase_creds = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace(r'\n', '\n'),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
        "universe_domain": st.secrets["firebase"]["universe_domain"],
    }

    cred = credentials.Certificate(firebase_creds)  # Load directly, no file writing
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Load Firebase config for Pyrebase
def init_firebase():
    firebase_config = {
        "apiKey": st.secrets["firebase"]["apiKey"],  
        "authDomain": f"{st.secrets['firebase']['project_id']}.firebaseapp.com",
        "databaseURL": f"https://{st.secrets['firebase']['project_id']}.firebaseio.com",
        "projectId": st.secrets["firebase"]["project_id"],
        "storageBucket": f"{st.secrets['firebase']['project_id']}.appspot.com",
        "messagingSenderId": st.secrets["firebase"]["client_id"],
        "appId": st.secrets["firebase"].get("app_id", ""),
        "measurementId": st.secrets["firebase"].get("measurement_id", "")
    }
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
            background-image: linear-gradient(to right, white, white, #white);
        }
        hr.style-one-grid {
            border: 0;
            height: 1px !important;
            margin-top: -10px;
            margin-bottom: -100px;
            background: #333;
            background-image: linear-gradient(to right, white, white, white);
        }
        .hyperlink {
            text-decoration: none !important;
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
                    st.error("❌ User data not found. Please register.")
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

CLOUD_NAME = "dusq8j5cp"
UPLOAD_PRESET = "unsigned_upload"
CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"

# cloudinary upload

def upload_to_cloudinary(image):
    """Uploads an image to Cloudinary and returns the URL."""
    try:
        # Auto-orient the image based on EXIF data
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == "Orientation":
                    break
            exif = image._getexif()
            if exif is not None and orientation in exif:
                if exif[orientation] == 3:
                    image = image.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    image = image.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass  # No EXIF data, ignore rotation

        image = image.convert("RGB")
        max_size = 1024
        image.thumbnail((max_size, max_size))  # Resize while keeping aspect ratio

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")  # Save image as PNG
        img_bytes.seek(0)

        # Prepare request payload
        files = {"file": img_bytes}
        data = {"upload_preset": UPLOAD_PRESET}

        # Upload to Cloudinary
        response = requests.post(CLOUDINARY_URL, files=files, data=data)

        if response.status_code == 200:
            return response.json().get("secure_url")  # Return the image URL
        else:
            st.error("Failed to upload image.")
            return None
    except Exception as e:
        st.error(f"Image processing or upload error: {e}")
        return None

def to_signup():
    st.markdown('<div class="container">', unsafe_allow_html=True)
    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
    st.markdown('<div class="title">Create an Account</div>', unsafe_allow_html=True)

    # Name Fields
    cola1, cola2, cola3 = st.columns([1,1,1])
    with cola1: first_name = st.text_input("First Name", key="first_name").strip()
    with cola2: middle_name = st.text_input("Middle Name (Optional)", key="middle_name").strip()
    with cola3: last_name = st.text_input("Last Name", key="last_name").strip()

    # Email Fields
    colb1, colb2 = st.columns([1,1])
    with colb1: email = st.text_input("Enter your email", key="email", placeholder="example@example.com").strip()
    with colb2: confirm_email = st.text_input("Confirm your email", key="confirm_email", placeholder="example@example.com").strip()
    
    # Password Fields
    colc1, colc2 = st.columns([1,1])
    with colc1: password = st.text_input("Enter your password", type="password", key="password").strip()
    with colc2: confirm_password = st.text_input("Confirm your password", type="password", key="confirm_password").strip()

    # Mobile Number
    phone_code_url = "https://country.io/phone.json"
    try:
        response = requests.get(phone_code_url)
        country_data = response.json()

        country_codes = sorted([
            f"{country} +{code.lstrip('+')}" 
            for country, code in country_data.items()
        ])
    except Exception as e:
        st.error(f"Failed to load country codes: {e}")
        country_codes = ["US +1", "GB +44", "AU +61", "IN +91", "PH +63", "JP +81", "CN +86"]  # Fallback list

    cold1, cold2 = st.columns([1,3])
    with cold1: country_code = st.selectbox("Country Code", country_codes, key="country_code")
    with cold2: mobile_number = st.text_input("Mobile Number", key="mobile_number", placeholder="9123456789").strip()

    # Address Field
    address = st.text_area("Enter your address (House No., Street, City, State, Zip Code, Country)", key="address").strip()

    cole1, cole2 = st.columns([1,1])
    with cole1:
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
    with cole2: 
        gender = st.selectbox(
            "Gender",
            [
                "Male",
                "Female",
                "Non-binary",
                "Agender",
                "Genderfluid",
                "Transgender Male",
                "Transgender Female",
                "Prefer to Self-Describe",
                "Prefer Not to Say",
                "Others",
            ],
            key="gender",
        )

    uploaded_file = st.file_uploader("Upload personal picture", type=["png", "jpg", "jpeg"])
    st.markdown(
        """<div style=""><br>By creating an account, you agree to our <b>Terms and Conditions</b> and <b>Privacy Policy</b>, 
            and you consent to <b><a class="hyperlink" href="https://github.com/ysls-ctu">YSLS</a></b> storing and processing your personal data in accordance with 
            the <b><a class="hyperlink" href="https://privacy.gov.ph/data-privacy-act/">Republic Act 10173 - Data Privacy Act of 2012</a></b>.<br></div>""", unsafe_allow_html=True
    )
    "\n"
    agreed_to_terms = st.checkbox("I agree to the Terms & Conditions and Privacy Policy", key="terms")
    termscol1, termscol2 = st.columns([1,1])
    with termscol1: 
        with st.expander("View Terms and Conditions"):
            st.markdown("### Terms and Conditions")
            st.markdown("""
            This document outlines the rules users must agree to before using the Personal Expense Tracker.
            <ol>
                <li><b>Acceptance of Terms</b>
                <br>By signing up, you agree to abide by these Terms and Conditions. If you do not agree, you must not use this application.</li>
                <li><b>Account Registration</b>
                <ul>
                    <li>Users must provide accurate personal information.</li>
                    <li>Users are responsible for maintaining the confidentiality of their login credentials.</li>
                    <li>The developer (YSLS) reserves the right to suspend or terminate accounts that violate these terms.</li>
                </ul></li>
                <li><b>Data Storage & Processing</b>
                <ul>
                    <li>The app collects and stores names, email addresses, mobile numbers, addresses, birthdays, and profile pictures for account creation and service functionality.</li>
                    <li>Data is securely stored in Firebase and is only used for account management and personalization.</li>
                    <li>The developer (YSLS) will not sell or share your data with third parties for marketing purposes.</li>
                </ul></li>
                <li><b>User Responsibilities</b>
                <ul>
                    <li>Users must ensure their account security and not share login credentials.</li>
                    <li>Users must not misuse the app for illegal activities.</li>
                    <li>Any attempt to breach the security or functionality of the application may result in legal action.</li>
                </ul></li>
                <li><b>Disclaimer of Liability</b>
                <ul>
                    <li>The developer (YSLS) provides the app "as-is" without warranties regarding accuracy, reliability, or availability.</li>
                    <li>The app is designed for personal expense tracking only and should not be relied upon for financial or legal decisions.</li>
                </ul></li>
                <li><b>Termination of Account</b>
                <ul>
                    <li>The developer (YSLS) reserves the right to terminate accounts that violate terms, engage in fraud, or pose security risks.</li>
                    <li>Users may request account deletion at any time.</li>
                </ul></li>
                <li><b>Amendments</b>
                <ul>
                    <li>The developer (YSLS) may update these Terms and Conditions. Continued use of the app signifies acceptance of any modifications.</li>
                </ul></li><br>
            </ol>
        """, unsafe_allow_html=True)
    with termscol2:
        with st.expander("View Privacy Policy"):
            st.markdown("### Privacy Policy")
            st.markdown("""
            This policy explains how your personal data is collected, used, and protected in compliance with the Republic Act 10173 - Data Privacy Act of 2012.
            <ol>
                <li><b>Data Collected</b>
                <br>When signing up, we collect:
                <ul>
                    <li>Personal Information: Full name, email, phone number, address, birthday, gender.
                    <li>Profile Picture: Uploaded images for personalization.
                    <li>Device & Usage Data: IP address, browser type, and interactions with the app.
                </ul>
                <li><b>Purpose of Data Collection</b>
                <br>Your data is collected to:
                <ul>
                    <li>Create and manage your account.
                    <li>Securely authenticate users.
                    <li>Personalize and enhance the user experience.
                    <li>Ensure compliance with security regulations.
                </ul>
                <li><b>Data Protection & Security</b>
                <ul>
                    <li>All personal data is stored securely in Firebase.
                    <li>We implement encryption, access control, and secure authentication.
                    <li>We never sell user data to third parties.
                </ul>
                <li><b>Data Sharing</b>
                <br>Your data may be shared only under the following conditions:
                <ul>
                    <li>Legal Compliance: If required by law or government authorities.
                    <li>Service Improvement: With third-party services only for app functionality (e.g., Firebase, Cloudinary).
                </ul>
                <li><b>User Rights</b>
                <br>Under the Data Privacy Act of the Philippines, you have the right to:
                <ul>
                    <li>Access the personal data stored about you.
                    <li>Request Correction of inaccurate data.
                    <li>Request Deletion of your account and personal data.
                    <li>Withdraw Consent at any time.
                </ul>
                <li><b>Data Retention</b>
                <ul>
                    <li>We retain user data only as long as necessary for service functionality.
                    <li>Users may request data deletion via the account settings.
                </ul>
                <li><b>Changes to this Policy</b>
                <ul>
                    <li>We may update this Privacy Policy as needed. Users will be notified of significant changes.
                </ul><br>
            </ol>
        """, unsafe_allow_html=True
        )

    if st.button("Create Account", key="signup_btn", use_container_width=True):
        if agreed_to_terms:
            # Form validation
            if (
                not first_name 
                or not last_name 
                or not re.match(r'^[A-Za-z ]+$', first_name) 
                or (middle_name and not re.match(r'^[A-Za-z ]+$', middle_name))  # Validate only if middle_name is entered
                or not re.match(r'^[A-Za-z ]+$', last_name)
            ):
                st.error("⚠️ First and last names are required. Middle name is optional but must contain only letters and spaces if provided.")
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
            elif uploaded_file is None:
                st.error("⚠️ Please select a photo.")
            else:
                try:
                    # Create user in Firebase Authentication
                    user = auth_client.create_user_with_email_and_password(email, password)
                    auth_client.send_email_verification(user['idToken'])
                    user_id = user['localId']  # Unique ID of the user in Firebase Authentication

                    image_url = "https://asset.cloudinary.com/dusq8j5cp/c1bf196c3926aa24dd325f611192b0b3"
                    if uploaded_file:
                        image = Image.open(uploaded_file)
                        # Upload to Cloudinary
                        image_url = upload_to_cloudinary(image)
                            
                    # Store user data in Firestore
                    user_data = {
                        "first_name": first_name,
                        "middle_name": middle_name + " ",
                        "last_name": last_name,
                        "email": email,
                        "country_code": country_code,
                        "mobile_number": mobile_number,
                        "address": address,
                        "birthday": str(birthday),
                        "gender": gender,
                        "profile_picture": image_url,
                        "created_at": firestore.SERVER_TIMESTAMP,  # Timestamp for when the account was created
                    }

                    db.collection("users").document(user_id).set(user_data)  # Store user in Firestore

                    st.success("✅ Account created successfully! Please check your email for a verification link before logging in.")
                    time.sleep(5)
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
        else:
            st.error("⚠️ You must agree to the Terms & Conditions and Privacy Policy to proceed.")

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

    if st.button("Send Password Reset Email", key="reset_password", use_container_width=True):
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

def get_user_data(user_email):
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", user_email).get()

    if query:
        return query[0].to_dict()  
    return None

def update_user_data(user_email, updated_data):
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", user_email).get()

    if query:
        doc_id = query[0].id  
        users_ref.document(doc_id).update(updated_data)
        return True
    return False

def to_analytics():
    if "user" in st.session_state:
        user = st.session_state["user"]

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        
        try:
            docs = db.collection("expenses").where("user", "==", user["email"]).stream()
            expenses = [{**doc.to_dict(), "id": doc.id} for doc in docs]
            
            if expenses:
                df = pd.DataFrame(expenses)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"])

                # Dropdown for selecting time frame
                st.markdown("<center><h3>Your Analytics Dashboard</h3></center>", unsafe_allow_html=True)
                time_frames = {"Current Month": 0, "Last Month": 1, "Last 3 Months": 3, "Last 6 Months": 6}
                selected_timeframe = st.selectbox("Select Time Frame:", list(time_frames.keys()))
                st.markdown("<br>", unsafe_allow_html=True)
                months_ago = time_frames[selected_timeframe]
                start_date = datetime.now().replace(day=1) - timedelta(days=30 * months_ago)
                df_filtered = df[df["date"] >= start_date]
                
                total_expenses = df_filtered["amount"].sum()
                daily_avg_spending = total_expenses / max(1, (datetime.now() - start_date).days)
                
                category_spending = df_filtered.groupby("category")["amount"].sum()
                highest_category = category_spending.idxmax() if not category_spending.empty else "N/A"
                highest_category_amount = category_spending.max() if not category_spending.empty else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Expenses", f"₱ {total_expenses:,.2f}")
                col2.metric("Daily Avg Spending", f"₱ {daily_avg_spending:,.2f}")
                col3.metric("Top Category", f"{highest_category}")
                st.divider()

                # Monthly Spending Projection
                projected_monthly_spending = daily_avg_spending * 30
                col1, col2 = st.columns(2)
                col1.metric("Projected Monthly Spending", f"₱ {projected_monthly_spending:,.2f}")

                # Financial Health Score Calculation
                if len(df_filtered) > 1:
                    std_spending = df_filtered["amount"].std()
                    median_spending = df_filtered["amount"].median()

                    # Score Calculation (Simple out of 100)
                    stability_factor = max(0, 100 - (std_spending / max(1, daily_avg_spending)) * 30)
                    consistency_factor = max(0, 100 - abs(daily_avg_spending - median_spending) * 2)
                    score = int((stability_factor + consistency_factor) / 2)

                    col2.metric("Financial Health Score", f"{score}/100")
                
                    # Budgeting Advice
                    st.markdown("<h5>💡 Budgeting Advice</h5>", unsafe_allow_html=True)

                    if score > 75:
                        st.success("Your spending is well-managed and consistent. Consider setting savings goals to further enhance your financial health.")
                    elif score > 50:
                        st.warning("Your spending habits are relatively stable, but there are occasional fluctuations. Try tracking high-value purchases to maintain balance.")
                    else:
                        st.error("Your spending is highly unpredictable. Consider setting a weekly budget and monitoring discretionary expenses.")

                st.divider()
                with st.expander("View Visual Analytics"):
                    # Category Pie Chart
                    if not category_spending.empty:
                        fig, ax = plt.subplots(figsize=(6, 6))
                        ax.pie(category_spending, labels=category_spending.index, autopct="%1.2f%%", startangle=140, colors=sns.color_palette("pastel"))
                        ax.set_title("Category-wise Spending", fontsize=12, fontweight="bold")
                        st.pyplot(fig)
                        st.divider()
                    
                    # Expense Trend Line Chart
                    df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
                    df_filtered = df_filtered.dropna(subset=["date"])
                    df_filtered["date"] = df_filtered["date"].dt.date
                    daily_trend = df_filtered.groupby("date")["amount"].sum()
                    
                    if not daily_trend.empty:
                        fig, ax = plt.subplots(figsize=(8, 4))
                        sns.lineplot(x=daily_trend.index, y=daily_trend.values, marker="o", ax=ax, color="royalblue")
                        ax.set_title("Spending Trend Over Time", fontsize=14, fontweight="bold")
                        ax.set_xlabel("Date")
                        ax.set_ylabel("Amount Spent (₱)")
                        ax.grid(True, linestyle="--", alpha=0.5)
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
                        st.divider()
                    
                    # Weekly Breakdown Bar Chart
                    df_filtered["week"] = df_filtered["date"].apply(lambda x: x.strftime("%W"))
                    weekly_spending = df_filtered.groupby("week")["amount"].sum()
                    
                    if not weekly_spending.empty:
                        fig, ax = plt.subplots(figsize=(8, 4))
                        sns.barplot(x=weekly_spending.index, y=weekly_spending.values, ax=ax, palette="coolwarm")
                        ax.set_title("Weekly Spending Breakdown", fontsize=14, fontweight="bold")
                        ax.set_xlabel("Week")
                        ax.set_ylabel("Total Spending (₱)")
                        st.pyplot(fig)
                
                with st.expander("View Spending Habits Summary"):
                    df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
                    st.markdown('<center><h3 style="margin-bottom:10px;">Detailed Summary of Your Spending Habits</h3></center>', unsafe_allow_html=True)

                    def display_info(column, label, value, full_width=False):
                        """Displays user information in a column or full-width."""
                        formatted_value = value if value else no_data
                        markdown = f"<p style='margin-bottom: 5px;'><b>{label} </b></p>"
                        
                        if full_width:
                            st.markdown(markdown, unsafe_allow_html=True)
                            st.success(formatted_value)
                        else:
                            column.markdown(markdown, unsafe_allow_html=True)
                            column.success(formatted_value)

                    # Overview
                    st.markdown("<h5>Overall Spending Trends</h5>", unsafe_allow_html=True)
                    no_data = "No data"
                    col1, col2 = st.columns(2)
                    display_info(col1, "Total Spending for the Selected Period", f"₱ {total_expenses:,.2f}")
                    display_info(col1, "Number of Transactions", f"{len(df_filtered)}")
                    display_info(col2, "Daily Average Spending", f"₱ {daily_avg_spending:,.2f}")
                    highest_transaction = df_filtered.loc[df_filtered['amount'].idxmax()]  
                    if not df_filtered.empty:
                        highest_transaction = df_filtered.loc[df_filtered['amount'].idxmax()]
                        display_info(col2, "Highest Single Transaction", f"{highest_transaction['item_name']} (₱ {highest_transaction['amount']:,.2f})")
                    else:
                        display_info(col2, "Highest Single Transaction", "No transactions available")

                    st.divider()

                    # Category Breakdown
                    st.markdown("<h5>Category-Wise Spending</h5>", unsafe_allow_html=True)
                    col3, col4 = st.columns(2)
                    if not df_filtered.empty:
                        display_info(col3, "Highest Single Transaction", f"₱ {df_filtered['amount'].max():,.2f}")
                    else:
                        display_info(col3, "Highest Single Transaction", "No transactions available")

                    display_info(col4, "Most Expensive Category", f"{highest_category} (₱ {highest_category_amount:,.2f})")
                    st.divider()
                    st.markdown("<h5>Top 3 Categories with Highest Spending</h5>", unsafe_allow_html=True)
                    try:
                        if not category_spending.empty:
                            top_categories = category_spending.nlargest(3)
                        else:
                            top_categories = {}

                        if top_categories is not None and not top_categories.empty:
                            number = 1
                            for category, amount in top_categories.items():
                                col1, col2 = st.columns([1, 1])  
                                with col1:
                                    st.info(f"**{number} - {category}**")  
                                with col2:
                                    st.success(f"₱ {amount:,.2f}") 
                                number += 1
                        else:
                            st.warning("No spending data available")
                    except Exception as e:
                        st.warning(f"Check top categories: {e}")



                    st.divider()

                    # Weekly Insights
                    if not df_filtered["date"].isnull().all():
                        df_filtered["week"] = df_filtered["date"].dt.strftime("%W")  # Convert to week number
                        weekly_spending = df_filtered.groupby("week")["amount"].sum()

                        st.markdown("<h5>Weekly Spending Patterns</h5>", unsafe_allow_html=True)
                        col5, col6, col7 = st.columns([1,1,1])
                        if not weekly_spending.empty:
                            display_info(col5, "Highest Spent", f"Week {weekly_spending.idxmax()} (₱ {weekly_spending.max():,.2f})")
                            display_info(col6, "Lowest Spent", f"Week {weekly_spending.idxmin()} (₱ {weekly_spending.min():,.2f})")
                            display_info(col7, "Average Spent (Week)", f"₱ {weekly_spending.mean():,.2f}")
                    st.divider()

                    # Spending Behavior
                    st.markdown("<h5>Spending Behavior Analysis</h5>", unsafe_allow_html=True)
                    if len(df_filtered) > 1:
                        avg_spending = df_filtered['amount'].mean()
                        std_spending = df_filtered['amount'].std()
                        median_spending = df_filtered['amount'].median()
                        # Standard Deviation Analysis
                        if std_spending > 0.75 * avg_spending:
                            sd_interpretation = (
                                "Your spending is highly inconsistent, with large fluctuations between purchases. "
                                "This suggests impulsive spending habits or occasional big-ticket purchases that disrupt budgeting. "
                                "Consider tracking high-value transactions to manage cash flow better."
                            )
                        elif std_spending < 0.25 * avg_spending:
                            sd_interpretation = (
                                "Your spending is highly stable, indicating consistent financial habits. "
                                "This means you generally stick to a routine budget without major unexpected expenses. "
                                "If intentional, this is a great sign of financial control."
                            )
                        else:
                            sd_interpretation = (
                                "Your spending pattern is moderately stable, with occasional variations. "
                                "While you generally maintain consistent spending, some purchases deviate from the norm. "
                                "Reviewing these variations can help fine-tune budgeting strategies."
                            )
                        # Median Transaction Analysis
                        if median_spending < 0.5 * avg_spending:
                            median_interpretation = (
                                "The majority of your transactions are small, but a few high-value purchases significantly raise your average spending. "
                                "This suggests a pattern of frequent small expenses combined with occasional major transactions. "
                                "To maintain control, consider setting aside funds for these large purchases in advance."
                            )
                        elif median_spending > 1.5 * avg_spending:
                            median_interpretation = (
                                "You frequently engage in high-value transactions, suggesting a preference for larger purchases over small, frequent expenses. "
                                "This could mean you invest in high-quality or bulk purchases rather than daily expenditures. "
                                "Ensure these are planned to avoid financial strain."
                            )
                        else:
                            median_interpretation = (
                                "Your spending is balanced, meaning both small and large transactions occur in a relatively even distribution. "
                                "This indicates a mix of daily expenses and occasional bigger purchases, reflecting a well-rounded spending habit."
                            )
                        # Display Results
                        colx1,colx2 = st.columns([1,1])
                        with colx1: display_info(None, "Standard Deviation of Spending", f"₱ {std_spending:,.2f}", full_width=True)
                        with colx2: display_info(None, "Average Transaction Amount", f"₱ {avg_spending:,.2f}", full_width=True)
                        st.caption("Standard deviation measures how spread out your spending is from the average.")

                        st.info(sd_interpretation)
                        display_info(None, "Median Transaction Amount", f"₱ {median_spending:,.2f}", full_width=True)
                        st.caption("The median is the middle value in your transactions — it tells you what a ‘typical’ spending amount looks like, unaffected by unusually large or small purchases.")
                        st.info(median_interpretation)
                    else:
                        st.info("Not enough transactions to analyze spending behavior.")
                    st.divider()

                    # Spending Frequency
                    st.markdown("<h5>Frequency of Transactions</h5>", unsafe_allow_html=True)
                    if not df_filtered.empty:
                        most_frequent_category = df_filtered["category"].mode()[0]
                        most_frequent_day = df_filtered["date"].mode()[0]  # Get the most frequent date
                        most_frequent_day_str = most_frequent_day.strftime("%B %d, %Y")  
                        most_frequent_day_total = df_filtered[df_filtered["date"] == most_frequent_day]["amount"].sum()  

                        avg_transactions_per_day = len(df_filtered) / datetime.now().day
                        total_spending = df_filtered["amount"].sum()

                        col8, col9 = st.columns([1,1])
                        display_info(col8, "Most Frequently Purchased Category", f"{most_frequent_category}")
                        display_info(col8, "Average Transactions Per Day", f"{avg_transactions_per_day:.2f}")
                        display_info(col9, "Day with the Most Spending", f"{most_frequent_day_str} (₱ {most_frequent_day_total:,.2f})")
                        display_info(col9, "Total Spending", f"₱ {total_spending:,.2f}")
                    else:
                        st.info("No recorded transactions for frequency analysis")
                    st.divider()
                    
                    df_filtered["date"] = pd.to_datetime(df_filtered["date"], errors="coerce")
                    df_filtered["date"] = df_filtered["date"].dt.date

                    # Data Table
                    st.markdown("<h5>Expenses History</h5>", unsafe_allow_html=True)
                    column_mapping = {"date": "Purchase Date", "item_name": "Item Name", "amount": "Amount (₱)", "category": "Category", "notes": "Notes"}
                    df_filtered.rename(columns=column_mapping, inplace=True)
                    df_filtered = df_filtered[list(column_mapping.values())]
                    st.dataframe(df_filtered, height=560, use_container_width=True, hide_index=True)

                    timestamp = datetime.now().strftime("%H%M%S.%y%m%d")
                    file_name = f"expenses_report.{timestamp}.csv"

                    # Convert DataFrame to CSV format (in-memory buffer)
                    csv_buffer = io.StringIO()
                    df_filtered.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()

                    dlcol1, dlcol2 = st.columns([2,1])
                    with dlcol2:
                        st.download_button(
                            label="Download Report (.csv)",
                            data=csv_data,
                            file_name=file_name,
                            mime="text/csv",
                            use_container_width=True,
                        )
            else:
                st.info("ℹ️ No expenses recorded yet.")
        except Exception as e:
            st.error(f"❌ Error fetching expenses: {e}")
            st.info("empty")

        

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state["page"] = "Dashboard"
            st.rerun()
    else:
        st.warning("⚠️ Please log in to access the dashboard.")

def to_profile():
    if "user" in st.session_state:
        user = st.session_state["user"]

        try:
            user_query = db.collection("users").where("email", "==", user["email"]).limit(1).stream()
            user_data = next(user_query, None)
            user_email = user_data.to_dict().get("email", "User") if user_data else "User"
        except Exception as e:
            st.error(f"❌ Error fetching user data: {e}")
            first_name = "User"

        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown('<div class="title">Profile & Information</div>', unsafe_allow_html=True)
        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        user_data = get_user_data(user_email)

        if user_data:
            try:
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: center;">
                        <img src="{user_data['profile_picture']}" alt="Profile Picture" 
                        style="max-width: 300px; max-height: 300px; border-radius: 10px; 
                         margin-bottom: 30px; object-fit: contain;">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"❌ Error fetching profile picture: {e}")

            no_data = "No data"
            col1, col2, col3 = st.columns(3)
            col4, col5 = st.columns(2)
            def display_info(column, label, value, full_width=False):
                """Displays user information in a column or full-width."""
                formatted_value = value if value else no_data
                markdown = f"<p style='margin-bottom: 5px;'><b>{label}:</b></p>"
                
                if full_width:
                    st.markdown(markdown, unsafe_allow_html=True)
                    st.info(formatted_value)
                else:
                    column.markdown(markdown, unsafe_allow_html=True)
                    column.info(formatted_value)

            display_info(col1, "First Name", user_data["first_name"])
            display_info(col2, "Middle Name", user_data["middle_name"])
            display_info(col3, "Last Name", user_data["last_name"])
            display_info(col4, "Gender", user_data["gender"])
            display_info(col4, "Email Address", user_data["email"])
            formatted_birthday = datetime.strptime(user_data["birthday"], "%Y-%m-%d").strftime("%B %d, %Y")
            display_info(col5, "Date of Birth", formatted_birthday)
            display_info(col5, "Mobile Number", f"{user_data['country_code']}{user_data['mobile_number']}")
            display_info(None, "Address", user_data["address"], full_width=True)

            col1, col2 = st.columns([1, 1])
            # Editable fields
            with st.expander("Edit Information"):
                st.info("Want to change your password? Request a password reset email by clicking the button below.")

                if st.button("Send Password Reset Email", key="reset_password", use_container_width=True):
                    email_pass = user_data["email"]
                    try:
                        auth_client.send_password_reset_email(email_pass)
                        st.success(f"✅ A password reset link has been sent to {email_pass}. Check your inbox.")
                    except Exception as e:
                        st.error("❌ Error sending reset email. Please try again.")
                uploaded_file = st.file_uploader("Upload a new personal picture", type=["png", "jpg", "jpeg"])
                colh1, colh2, colh3 = st.columns([1, 1, 1])
                with colh1: 
                    first_name = st.text_input("First Name", value=user_data["first_name"]).strip()
                with colh2: 
                    middle_name = st.text_input("Middle Name", value=user_data["middle_name"]).strip()
                with colh3: 
                    last_name = st.text_input("Last Name", value=user_data["last_name"]).strip()

                coli1, coli2 = st.columns([1, 1])
                with coli1:
                    gender_options = [
                        "Male", "Female", "Non-binary", "Agender", "Genderfluid", 
                        "Transgender Male", "Transgender Female", "Prefer to Self-Describe", 
                        "Prefer Not to Say", "Others"
                    ]
                    gender = st.selectbox("Gender", gender_options, index=gender_options.index(user_data["gender"]))
                
                with coli2:
                    today = date.today()
                    min_birthday = today - timedelta(days=365 * 100)
                    max_birthday = today

                    birthday = st.date_input(
                        "Date of Birth",
                        value=date.fromisoformat(user_data["birthday"]),
                        min_value=min_birthday,
                        max_value=max_birthday
                    )

                # Fetch country codes
                phone_code_url = "https://country.io/phone.json"
                try:
                    response = requests.get(phone_code_url)
                    country_data = response.json()
                    country_codes = sorted([f"{country} +{code.lstrip('+')}" for country, code in country_data.items()])
                except Exception as e:
                    st.error(f"Failed to load country codes: {e}")
                    country_codes = ["US +1", "GB +44", "AU +61", "IN +91", "PH +63", "JP +81", "CN +86"]  # Fallback list

                cold1, cold2 = st.columns([1, 3])
                with cold1:
                    country_code = st.selectbox("Country Code", country_codes, key="country_code")
                with cold2:
                    mobile_number = st.text_input("Mobile Number", value=user_data["mobile_number"], key="mobile_number").strip()
                
                address = st.text_area("Enter your address (House No., Street, City, State, Zip Code, Country)", 
                                    value=user_data["address"], key="address").strip()
                
                image_url = user_data["profile_picture"]
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    # Upload to Cloudinary
                    
                if st.button("Update Profile", use_container_width=True):
                    if (
                        not first_name 
                        or not last_name 
                        or not re.match(r'^[A-Za-z ]+$', first_name) 
                        or (middle_name and not re.match(r'^[A-Za-z ]+$', middle_name))  # Validate only if middle_name is entered
                        or not re.match(r'^[A-Za-z ]+$', last_name)
                    ):
                        st.error("⚠️ First and last names are required. Middle name is optional but must contain only letters and spaces if provided.")
                    elif not mobile_number or not mobile_number.isdigit():
                        st.error("⚠️ Mobile number is required and must be numeric.")
                    elif not address:
                        st.error("⚠️ Address field is required.")
                    elif gender not in gender_options:
                        st.error("⚠️ Please select a valid gender.")
                    else:
                        image_url = upload_to_cloudinary(image)
                        updated_data = {
                            "first_name": first_name,
                            "middle_name": middle_name,
                            "last_name": last_name,
                            "gender": gender,
                            "birthday": str(birthday),
                            "country_code": country_code,
                            "mobile_number": mobile_number,
                            "address": address,
                            "profile_picture": image_url,
                        }
                        if update_user_data(user_data["email"], updated_data):
                            st.success("✅ Profile updated successfully!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Failed to update profile.")                
        else:
            st.error("User data not found!")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        colg1, colg2 = st.columns([1,1])
        with colg1:
            if st.button("Back to Dashboard", use_container_width=True):
                st.session_state["page"] = "Dashboard"
                st.rerun()
        with colg2:
            if st.button("Logout", use_container_width=True):
                st.session_state.pop("user", None)
                st.session_state["page"] = "Login"
                st.rerun()  

def reset_form():
    st.session_state.purchased_date = date.today()
    st.session_state.amount = 0.00
    st.session_state.item_name = ""
    st.session_state.category = "Grocery"
    st.session_state.notes = ""

if "purchased_date" not in st.session_state:
    st.session_state.purchased_date = date.today()
if "amount" not in st.session_state:
    st.session_state.amount = 0.00
if "item_name" not in st.session_state:
    st.session_state.item_name = ""
if "category" not in st.session_state:
    st.session_state.category = "Grocery"
if "notes" not in st.session_state:
    st.session_state.notes = ""
    
def to_dashboard():
    if "user" in st.session_state:
        user = st.session_state["user"]
        
        try:
            user_query = db.collection("users").where("email", "==", user["email"]).limit(1).stream()
            user_data = next(user_query, None)
            first_name = user_data.to_dict().get("first_name", "User") if user_data else "User"
            user_email = user_data.to_dict().get("email", "User") if user_data else "User"
        except Exception as e:
            st.error(f"❌ Error fetching user data: {e}")
            first_name = "User"

        user_data = get_user_data(user_email)

        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown(f'<div class="title">Welcome, {first_name}!</div>', unsafe_allow_html=True)

        ppcol1, ppcol2, ppcol3 = st.columns([2,1,2])
        if user_data:
            with ppcol2:
                try:
                    st.markdown(
                        f"""
                            <div style="display: flex; justify-content: center;">
                                <img src="{user_data['profile_picture']}" alt="Profile Picture" 
                                    style="width: 100px; height: 100px;  border-radius: 100px; object-fit: cover; border: solid #333 5px">
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"❌ Error fetching profile picture: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.date_input("Purchase Date", key="purchased_date")
            st.number_input("Item Amount (₱)", min_value=0.0, step=0.01, key="amount")

        with col2:
            st.text_input("Item Name", placeholder="Enter item name", key="item_name")
            st.selectbox("Item Category", [
                "Grocery", "Eat Out", "Transportation", "Entertainment", "Donation", "Education", 
                "Personal Care", "Health & Wellness", "Bills & Utilities", "Travel", "Subscription", 
                "Debt Payment", "Others"
            ], key="category")

        st.text_area("Notes (Optional)", key="notes")

        st.markdown('<br>', unsafe_allow_html=True)

        # Button logic
        if st.button("Add Expense", use_container_width=True):
            if not st.session_state.item_name:
                st.warning("⚠️ Please enter an item name.")
            elif not st.session_state.category:
                st.warning("⚠️ Please select a category.")
            elif st.session_state.amount <= 0:
                st.warning("⚠️ Amount must be greater than 0.")
            else:
                try:
                    db.collection("expenses").add({
                        "user": user["email"],
                        "date": st.session_state.purchased_date.strftime("%Y-%m-%d"),
                        "amount": st.session_state.amount,
                        "item_name": st.session_state.item_name,
                        "category": st.session_state.category,
                        "notes": st.session_state.notes  
                    })

                    st.success("✅ Expense added successfully!")
                    st.balloons()
                    rcol1,rcol2,rcol3 = st.columns([1,1,1])
                    with rcol2: st.button("Reset Form", on_click=reset_form, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Error adding expense: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        st.subheader("Your Expenses History")

        try:
            # Fetch expenses from Firestore
            docs = db.collection("expenses").where("user", "==", user["email"]).stream()
            expenses = [{**doc.to_dict(), "id": doc.id} for doc in docs]

            if expenses:
                df = pd.DataFrame(expenses)
                
                # Column mappings
                column_mapping = {
                    "date": "Purchase Date",
                    "item_name": "Item Name",
                    "amount": "Amount (₱)",
                    "category": "Category",
                    "notes": "Notes"
                }
                df.rename(columns=column_mapping, inplace=True)
                
                # Remove 'last_updated' if exists
                if "last_updated" in df.columns:
                    df.drop(columns=["last_updated"], inplace=True)
                
                # Keep ID for updates but hide in UI
                df = df[list(column_mapping.values()) + ["id"]]

                # --- SEARCH FUNCTIONALITY ---
                search_query = st.text_input("Search your expenses", "", placeholder="Type here").strip().lower()

                if search_query:
                    search_tokens = search_query.split()
                    filtered_df = df[df.apply(lambda row: all(any(token in str(value).lower() for value in row) for token in search_tokens), axis=1)]
                else:
                    filtered_df = df.copy()

                # Only proceed if filtered_df has results
                if not filtered_df.empty:
                    # Add selection column for deletion
                    filtered_df["Delete?"] = False

                    # --- UNIFIED TABLE (EDIT + DELETE) ---
                    edited_df = st.data_editor(
                        filtered_df.drop(columns=["id"]),
                        height=560,
                        use_container_width=True,
                        hide_index=True,
                        column_config={"Delete?": st.column_config.CheckboxColumn()},
                    )

                    # --- DETECT EDITS & UPDATE FIRESTORE ---
                    if "edited_expenses" not in st.session_state:
                        st.session_state.edited_expenses = filtered_df.copy()

                    if not edited_df.equals(st.session_state.edited_expenses):
                        st.session_state.edited_expenses = edited_df.copy()

                        updates = {}  # Store only changed rows
                        for i, row in edited_df.iterrows():
                            original_row = filtered_df.loc[i]  # Get original data
                            doc_id = original_row["id"]

                            # Check changed fields
                            updated_fields = {"last_updated": firestore.SERVER_TIMESTAMP}
                            for col_ui, col_db in column_mapping.items():
                                if row[col_db] != original_row[col_db]:
                                    updated_fields[col_ui] = row[col_db]

                            if len(updated_fields) > 1:  # If fields changed, update Firestore
                                updates[doc_id] = updated_fields  

                        if updates:
                            batch = db.batch()
                            for doc_id, fields in updates.items():
                                doc_ref = db.collection("expenses").document(doc_id)
                                batch.update(doc_ref, fields)
                            batch.commit()
                            st.success("✅ Changes saved successfully!")
                            ref1, ref2, ref3 = st.columns([1,3,1])
                            # Refresh button to reload table after saving
                            with ref2:
                                if st.button("🔄 Refresh Table", use_container_width=True):
                                    st.experimental_rerun()

                    # --- DELETE FUNCTIONALITY ---
                    selected_ids = filtered_df[edited_df["Delete?"]]["id"].tolist()

                    if selected_ids:
                        if st.button("🗑️ Delete Selected", use_container_width=True):
                            batch = db.batch()
                            for doc_id in selected_ids:
                                batch.delete(db.collection("expenses").document(doc_id))
                            batch.commit()
                            st.success("✅ Selected expenses deleted successfully!")
                            ref1, ref2, ref3 = st.columns([1,3,1])
                            # Refresh button to reload table after saving
                            with ref2:
                                if st.button("🔄 Refresh Table", use_container_width=True):
                                    st.experimental_rerun()
                else:
                    st.markdown(
                        """
                        <div style="text-align: center; padding: 20px;">
                            <p style="font-size:20px;">No results found. Try again!</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("ℹ️ No expenses recorded yet.")

        except Exception as e:
            st.error(f"❌ Error fetching expenses: {e}")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("View Profile & Information", use_container_width=True):
                st.session_state["page"] = "Profile"
                st.rerun()
            if st.button("Send Feedback", use_container_width=True):
                st.session_state["page"] = "Send Feedback"
                st.rerun()

        with col2:
            if st.button("View Detailed Analytics", use_container_width=True):
                st.session_state["page"] = "Analytics"
                st.rerun()
            if st.button("View Message Center", use_container_width=True):
                st.session_state["page"] = "Contact YSLS"
                st.rerun()
        
        st.divider()
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            if st.button("Logout", use_container_width=True):
                    st.session_state.pop("user", None)
                    st.session_state["page"] = "Login"
                    st.rerun()  
    else:
        st.warning("⚠️ Please log in to access the dashboard.")

def to_feedback():
    if "user" in st.session_state:
        user = st.session_state["user"]

        if "feedback_cat" not in st.session_state:
            st.session_state["feedback_cat"] = []
        if "feedback_text" not in st.session_state:
            st.session_state["feedback_text"] = ""
                
        try:
            user_query = db.collection("users").where("email", "==", user["email"]).limit(1).stream()
            user_data = next(user_query, None)
            first_name = user_data.to_dict().get("first_name", "User") if user_data else "User"
            user_email = user_data.to_dict().get("email", "User") if user_data else "User"
        except Exception as e:
            st.error(f"❌ Error fetching user data: {e}")
            first_name = "User"

        user_data = get_user_data(user_email)

        st.markdown('<div class="container">', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align: center; font-size: 29px; font-weight: 700; line-height: 1.1;">Hello, {first_name}! <br></div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; font-size: 20px; "><center>How can we help you today?<br><br></center></div>', unsafe_allow_html=True)

        with st.form("feedback_form"):
            feedback_cat = st.multiselect("Category", ["Bugs and Errors", "User Interface", "Feature Request", "Performace", "Security & Privacy", "General Feedback", "Other"], key="feedback_cat")
            feedback_text = st.text_area("Details", placeholder="Type your details here", key="feedback_text", height=250)
            is_anonymous = st.checkbox("Submit as Anonymous")


            "\n"
            col1,col2,col3 = st.columns([1,2,1])
            with col2: submit_button = st.form_submit_button("Submit Feedback", use_container_width=True)
    
            if submit_button:
                if not st.session_state.feedback_cat:
                    st.error("⚠️ Please provide feedback category!")
                elif not st.session_state.feedback_text.strip():
                    st.error("⚠️ Please provide feedback details!")
                else:
                    try:
                        # Prepare feedback data
                        feedback_data = {
                            "user_email": "Anonymous" if is_anonymous else user["email"],
                            "categories": st.session_state.feedback_cat,
                            "description": st.session_state.feedback_text.strip(),
                            "timestamp": firestore.SERVER_TIMESTAMP
                        }

                       # Save to Firestore
                        db.collection("feedback").add(feedback_data)

                        st.success("✅ Feedback submitted successfully! Refreshing ... ")

                        del st.session_state["feedback_cat"]
                        del st.session_state["feedback_text"]

                        time.sleep(1)
                        st.rerun()  

                    except Exception as e:
                        st.error(f"❌ Failed to submit feedback: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        colg1, colg2 = st.columns([1,1])
        with colg1:
            if st.button("Back to Dashboard", use_container_width=True):
                st.session_state["page"] = "Dashboard"
                st.rerun()
        with colg2:
            if st.button("Contact YSLS", use_container_width=True):
                st.session_state["page"] = "Contact YSLS"
                st.rerun()

def to_contactYSLS():

    st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
    def get_user_data(email):
        try:
            user_doc = db.collection("users").where("email", "==", email).limit(1).stream()
            user_data = next(user_doc, None)  # Prevent StopIteration error
            return user_data.to_dict() if user_data else {}  # Return empty dict instead of None
        except Exception as e:
            st.error(f"Error fetching user data: {e}")
            return {}  # Return empty dict on error

    def get_conversations(user_email):
        try:
            conv_docs = db.collection("conversations").where("participants", "array_contains", user_email).stream()
            conversations = {}

            for doc in conv_docs:
                convo_data = doc.to_dict()
                other_participant_email = [p for p in convo_data["participants"] if p != user_email][0]
                
                # Ensure the other participant exists
                other_participant_data = get_user_data(other_participant_email)  
                if not other_participant_data:  # If user does not exist
                    continue  # Skip this conversation

                other_participant_name = f"{other_participant_data.get('first_name', 'Unknown')} {other_participant_data.get('last_name', '')}".strip()
                conversations[doc.id] = {
                    "id": doc.id,
                    "participant": other_participant_name,
                    "email": other_participant_email
                }

            return conversations
        except Exception as e:
            st.error(f"Error fetching conversations: {e}")
            return {}

    def get_messages(conversation_id):
        try:
            messages = db.collection("conversations").document(conversation_id).collection("messages").order_by("timestamp").stream()
            return [msg.to_dict() for msg in messages]
        except Exception as e:
            st.error(f"Error fetching messages: {e}")
            return []

    def send_message(conversation_id, sender, message):
        try:
            db.collection("conversations").document(conversation_id).collection("messages").add({
                "sender": sender,
                "message": message,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            # st.rerun()

        except Exception as e:
            st.error(f"Error sending message: {e}")
            
    if "message_cont" not in st.session_state:
        st.session_state["message_cont"] = ""

    if "last_message" not in st.session_state:
        st.session_state["last_message"] = ""

    # Define the function to send the message and clear the input
    def send_message_and_clear():
        if st.session_state.message_cont.strip():  # Avoid sending empty messages
            send_message(selected_convo, user_email, st.session_state.message_cont)
            st.session_state.last_message = st.session_state.message_cont  # Store last sent message
            st.session_state.message_cont = ""  # Clear input field

    def start_new_conversation(user_email, recipient_email):
        try:
            existing_convo = db.collection("conversations").where("participants", "array_contains", user_email).stream()
            for convo in existing_convo:
                if recipient_email in convo.to_dict()["participants"]:
                    return convo.id
            convo_ref = db.collection("conversations").add({
                "participants": [user_email, recipient_email],
                "created_at": firestore.SERVER_TIMESTAMP
            })
            return convo_ref[1].id
        except Exception as e:
            st.error(f"Error starting conversation: {e}")
        
    if "user" in st.session_state:
        user = st.session_state["user"]
        user_data = get_user_data(user["email"])
        user_email = user_data.get("email", "User") if user_data else "User"
        
        st.title("Message Center")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Contacts")
            conversations = get_conversations(user_email)
            selected_convo = st.session_state.get("selected_convo", None)
            
            if conversations:
                convo_options = {convo["participant"]: convo_id for convo_id, convo in conversations.items()}

                selected_participant = st.selectbox("Select a conversation:", list(convo_options.keys()), key="selected_convo_dropdown")

                # Update session state when selection changes
                if selected_participant:
                    st.session_state["selected_convo"] = convo_options[selected_participant]
                    st.session_state["selected_user"] = selected_participant
            else:
                st.warning("No conversations yet. Start a new one below!")

            st.subheader("New Message")
            "\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
            "\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
            "\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
            new_user_email = st.text_input("Enter recipient email")
            if st.button("Start Conversation", use_container_width=True) and new_user_email:
                # Validate email format (basic check)
                if "@" not in new_user_email or "." not in new_user_email:
                    st.error("Invalid email format. Please enter a valid email address.")
                else:
                    # Check if the recipient exists in Firestore
                    recipient_data = get_user_data(new_user_email)

                    if recipient_data is None:
                        st.error("User not found. Please enter a registered email.")
                    else:
                        convo_id = start_new_conversation(user_email, new_user_email)
                        if convo_id:
                            st.session_state["selected_convo"] = convo_id
                            st.session_state["selected_user"] = f"{recipient_data.get('first_name', 'Unknown')} {recipient_data.get('last_name', '')}".strip()
                    
        with col2:
            if "selected_convo" in st.session_state and "selected_user" in st.session_state:
                selected_convo = st.session_state["selected_convo"]
                selected_user = st.session_state["selected_user"]

                def get_sender_name(email):
                    if email == user_email:
                        return user["first_name"] + " " + user["last_name"] # Show 'You' when the message is from the logged-in user
                    return selected_user

                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 10px; padding: 10px;">
                        <span style="font-size: 17px; font-weight: 600; color: #292929; margin-bottom: -10px; background-color: #f0f2f6; width: 100%; border-radius: 10px; padding: 10px;"><center>{selected_user}</center></span>
                    </div>
                    """,
                    unsafe_allow_html=True)
                chat_html = '''
                    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap" rel="stylesheet">
                    <div id="chat-container" class="chat-container" 
                        style="height: 400px; overflow-y: auto; display: flex; flex-direction: column-reverse; 
                        padding: 15px; background-color: #f0f2f6; border-radius: 5px; border: solid #f0f2f6 2px; 
                        font-family: 'Source Sans Pro', sans-serif;">
                '''
                
                messages = get_messages(selected_convo)  # Retrieve messages
                messages.reverse()

                for msg in messages:
                    is_user = msg["sender"] == user_email
                    dt = msg["timestamp"] if not isinstance(msg["timestamp"], str) else datetime.strptime(
                        msg["timestamp"].split(" at ")[0] + " " + msg["timestamp"].split(" at ")[1].split(" ")[0] + " " +
                        msg["timestamp"].split(" ")[-2], "%B %d, %Y %I:%M:%S %p")
                    military_time = dt.strftime("%B %d, %Y %H:%M")
                    alignment = "flex-end" if is_user else "flex-start"
                    bg_color = "#598ac2" if is_user else "white"
                    text_color = "white" if is_user else "black"

                    chat_html += f"""
                    <div style="display: flex; flex-direction: column; align-items: {alignment}; margin: 5px 0;">
                        <div class="chat-message" style="padding: 10px; border-radius: 10px; background-color: {bg_color}; color: {text_color}; 
                                    max-width: 75%; word-wrap: break-word;">
                            <div style="font-weight: 800; font-size: 13px;">
                                {get_sender_name(msg['sender'])}
                            </div> 
                            <div style="font-size: 14px;">
                                {msg['message']}
                            </div>
                            <div style="font-size: 10px; opacity: 0.7; text-align: right; display: block; margin-top:10px;">
                                {military_time}
                            </div>
                        </div>
                    </div>
                    """

                chat_html += "</div>"
                components.html(chat_html, height=450)

                # Input box for new messages
                st.markdown(
                    """
                    <style>
                        div[data-testid="stTextInput"] {
                            margin-top: -67px !important;
                            width: 97% !important;
                            margin: auto;
                        }

                    </style>
                    """,
                    unsafe_allow_html=True
                )

                st.text_input("", placeholder="Type your message here", key="message_cont", on_change=send_message_and_clear)

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        "\n\n"
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state["page"] = "Dashboard"
            st.rerun()

# header
col1, col_image, col3 = st.columns([1, 5, 1])
with col_image:
    # st.image("header_bg.png", width=1000)
    st.header("PERSONAL EXPENSE TRACKER")

# Sidebar Menu
menu = ["Login", "Sign Up", "Forgot Password", "Dashboard", "Analytics", "Profile", "Send Feedback", "Contact YSLS"]
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
elif st.session_state["page"] == "Analytics":
    to_analytics()
elif st.session_state["page"] == "Profile":
    to_profile()
elif st.session_state["page"] == "Send Feedback":
    to_feedback()
elif st.session_state["page"] == "Contact YSLS":
    to_contactYSLS()