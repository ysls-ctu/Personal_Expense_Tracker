import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase
import pandas as pd
from datetime import datetime, date, timedelta
import time
import json
import re
from PIL import Image
import io
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
import os
import subprocess

# Install pyrebase4 if not installed
try:
    import pyrebase
except ModuleNotFoundError:
    subprocess.run(["pip", "install", "pyrebase4"])
    import pyrebase  # Retry import after installing

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

CLOUD_NAME = "dusq8j5cp"
UPLOAD_PRESET = "unsigned_upload"
CLOUDINARY_URL = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"

def upload_to_cloudinary(image):
    """Uploads an image to Cloudinary and returns the URL."""
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
    elif uploaded_file is None:
        st.error("⚠️ Please select a photo.")
    else:
        if st.button("Create Account", key="signup_btn", use_container_width=True):
            try:
                # Create user in Firebase Authentication
                user = auth_client.create_user_with_email_and_password(email, password)
                auth_client.send_email_verification(user['idToken'])
                user_id = user['localId']  # Unique ID of the user in Firebase Authentication

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
                df["date"] = pd.to_datetime(df["date"])
                
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
                
                with st.expander("View Visual Analytics"):
                    # Category Pie Chart
                    if not category_spending.empty:
                        fig, ax = plt.subplots(figsize=(6, 6))
                        ax.pie(category_spending, labels=category_spending.index, autopct="%1.1f%%", startangle=140, colors=sns.color_palette("pastel"))
                        ax.set_title("Category-wise Spending", fontsize=12, fontweight="bold")
                        st.pyplot(fig)
                        st.divider()
                    
                    # Expense Trend Line Chart
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
                        st.divider()
                
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
                    display_info(col2, "Highest Single Transaction", f"{highest_transaction['item_name']} (₱ {highest_transaction['amount']:,.2f})")
                    st.divider()

                    # Category Breakdown
                    st.markdown("<h5>Category-Wise Spending</h5>", unsafe_allow_html=True)
                    col3, col4 = st.columns(2)
                    display_info(col3, "Highest Single Transaction", f"₱ {df_filtered['amount'].max():,.2f}")
                    display_info(col4, "Most Expensive Category", f"{highest_category} (₱ {highest_category_amount:,.2f})")
                    st.divider()
                    st.markdown("<h5>Top 3 Categories with Highest Spending</h5>", unsafe_allow_html=True)
                    top_categories = category_spending.nlargest(3)
                    number = 1
                    for category, amount in top_categories.items():
                        col1, col2 = st.columns([1,1])  
                        with col1:
                            st.info(f"**{number} - {category}**")  
                        with col2:
                            st.success(f"₱ {amount:,.2f}") 
                        number += 1
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
                        display_info(None, "Standard Deviation of Spending", f"₱ {std_spending:,.2f}", full_width=True)
                        st.info(sd_interpretation)
                        display_info(None, "Median Transaction Amount", f"₱ {median_spending:,.2f}", full_width=True)
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
                    
                    # Data Table
                    st.markdown("<h5>Expenses History</h5>", unsafe_allow_html=True)
                    column_mapping = {"date": "Purchase Date", "item_name": "Item Name", "amount": "Amount (₱)", "category": "Category", "notes": "Notes"}
                    df_filtered.rename(columns=column_mapping, inplace=True)
                    df_filtered = df_filtered[list(column_mapping.values())]
                    st.dataframe(df_filtered, height=560, use_container_width=True, hide_index=True)
                
            else:
                st.info("ℹ️ No expenses recorded yet.")
        except Exception as e:
            st.error(f"❌ Error fetching expenses: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state["page"] = "Dashboard"
            st.rerun()
    else:
        st.warning("⚠️ Please log in to access the dashboard.")

def to_profile():
    if "user" in st.session_state:
        user = st.session_state["user"]

        user_query = db.collection("users").where("email", "==", user["email"]).limit(1).stream()
        user_data = next(user_query, None)
        user_email = user_data.to_dict().get("email", "User") if user_data else "User"

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
                
                image_url = ""
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    # Upload to Cloudinary
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

                if st.button("Update Profile", use_container_width=True):
                    if not first_name or not last_name or not re.match(r'^[A-Za-z ]+$', first_name) or not re.match(r'^[A-Za-z ]+$', last_name):
                        st.error("⚠️ First and Last Name are required and must only contain letters and spaces.")
                    elif not mobile_number or not mobile_number.isdigit():
                        st.error("⚠️ Mobile number is required and must be numeric.")
                    elif not address:
                        st.error("⚠️ Address field is required.")
                    elif gender not in gender_options:
                        st.error("⚠️ Please select a valid gender.")
                    else:
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
        st.markdown(f'<div class="title">Welcome, {first_name}!</div>', unsafe_allow_html=True)
        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)

        # Expense Input Form
        col1, col2 = st.columns([1, 1])
        with col1:
            purchased_date = st.date_input("Purchase Date", date.today())
            amount = st.number_input("Item Amount (₱)", min_value=0.0, step=0.01)

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
            elif amount <= 0:
                st.warning("⚠️ Amount must be greater than 0.")
            else:
                try:
                    db.collection("expenses").add({
                        "user": user["email"],
                        "date": purchased_date.strftime("%Y-%m-%d"),
                        "amount": amount,
                        "item_name": item_name,
                        "category": category,
                        "notes": notes  
                    })
                    st.success("✅ Expense added successfully!")
                except Exception as e:
                    st.error(f"❌ Error adding expense: {e}")

        st.markdown('<hr class="style-two-grid">', unsafe_allow_html=True)
        st.subheader("Your Expenses History")
        try:
            docs = db.collection("expenses").where("user", "==", user["email"]).stream()
            expenses = [{**doc.to_dict(), "id": doc.id} for doc in docs]

            if expenses:
                df = pd.DataFrame(expenses)
                column_mapping = {
                    "date": "Purchase Date",
                    "item_name": "Item Name",
                    "amount": "Amount (₱)",
                    "category": "Category",
                    "notes": "Notes"
                }
                df.rename(columns=column_mapping, inplace=True)
                df = df[list(column_mapping.values())]
                st.dataframe(
                    df,
                    height=560,
                    use_container_width=True,  
                    hide_index=True
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

        with col2:
            if st.button("View Detailed Analytics", use_container_width=True):
                st.session_state["page"] = "Analytics"
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

col1, col_image, col3 = st.columns([1, 5, 1])
with col_image:
    st.image("header_bg.png", width=1000)

# Sidebar Menu
menu = ["Login", "Sign Up", "Forgot Password", "Dashboard", "Analytics", "Profile"]
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
