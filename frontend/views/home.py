import streamlit as st
import requests
import os 
from PIL import Image
import base64
import sys
import json

FAST_API_URL = "https://investorintel-backend-x4s2izvkca-uk.a.run.app/"

# Dynamically add project root (InvestorIntel.Ai/) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# ✅ Now do the imports
#from backend.database import investor_auth, investorIntel_entity

def render():
    # Session state defaults
    st.session_state.setdefault("user_type", None)
    st.session_state.setdefault("show_signup", False)

    # Layout
    col1, col2 = st.columns([1, 3], gap="large")

    # 🚪 Left Sidebar – Role Selection
    with col1:
        # 🔷 Add Logo
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "InvestorIntel_Logo.png"))
        logo = Image.open(logo_path)
        # Convert image to base64
        with open(logo_path, "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode()

        # Render centered image using HTML
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; padding-bottom: 10px;">
                <img src="data:image/png;base64,{encoded_logo}" width="300">
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("## 👋 Welcome")
        st.markdown("### Select Your Role")
        if st.button("🎯 I'm a Startup"):
            st.session_state.user_type = "Startup"
            st.session_state.show_signup = False  # reset view
        if st.button("💼 I'm an Investor"):
            st.session_state.user_type = "Investor"
            st.session_state.show_signup = False

    # 🖥️ Right Content – Info + Forms
    with col2:
        st.markdown("## 🚀 Welcome to InvestorIntel.ai")
        st.markdown("""
        InvestorIntel.ai is your bridge between visionary startups and smart investors.

        - **For Startups**: Submit your pitch deck and attract funding from top-tier investors.
        - **For Investors**: Discover high-potential startups, analyze metrics, and make informed decisions.

        Choose your role from the left to get started!
        """)

        # -------- STARTUP SECTION --------
        if st.session_state.user_type == "Startup":
            st.markdown("---")
            st.markdown("### 🚀 Pitch Deck Upload for Startups")
            st.markdown("""
            Upload your startup details and pitch deck. Our AI system will match your venture with relevant investors based on industry, growth metrics, and more.
            """)

            # Initialize once - add new funding fields
            for key, default in {
                "startup_name": "",
                "email_address": "",
                "funding_amount_requested": 0.0,
                "round_type": "Seed",
                "equity_offered": 0.0,
                "pre_money_valuation": 0.0,
                "industry": "",
                "website_url": "",
                "investors": [],
                "pitch_deck_uploaded": False,
                "pitch_deck_file": None
            }.items():
                st.session_state.setdefault(key, default)

            # Form fields
            st.session_state.startup_name = st.text_input("Startup Name", value=st.session_state.startup_name)
            
            # Email validation
            email = st.text_input("Contact Email", value=st.session_state.email_address)
            if email and not ("@" in email and "." in email.split("@")[1]):
                st.warning("Please enter a valid email address")
            st.session_state.email_address = email
            
            # Industry dropdown
            industries = ["AI", "Healthcare", "Tech Services", "Automotive", "Defense", "Entertainment", "Renewable Energy", "Fintech", "E-commerce", "Education"]
            st.session_state.industry = st.selectbox("Industry", options=industries, index=0 if not st.session_state.industry else industries.index(st.session_state.industry) if st.session_state.industry in industries else 0)

            # Website URL validation
            website_url = st.text_input("Website URL", value=st.session_state.website_url)
            if website_url and not (website_url.startswith("http://") or website_url.startswith("https://")):
                st.warning("Website URL should start with http:// or https://")
            st.session_state.website_url = website_url

            # New funding fields section
            st.markdown("### 💰 Funding Details")
            
            # Funding Amount Requested
            st.session_state.funding_amount_requested = st.number_input(
                "Funding Amount Requested (USD)", 
                min_value=0.0, 
                format="%.2f", 
                value=st.session_state.funding_amount_requested
            )
            
            # Round Type dropdown
            round_types = ["Seed", "Series A", "Series B", "Series C", "Convertible Note", "SAFE"]
            st.session_state.round_type = st.selectbox(
                "Round Type", 
                options=round_types, 
                index=round_types.index(st.session_state.round_type) if st.session_state.round_type in round_types else 0
            )
            
            # Equity Offered percentage with validation
            equity_offered = st.number_input(
                "Equity Offered (%)", 
                min_value=0.0, 
                max_value=100.0,
                format="%.2f", 
                value=st.session_state.equity_offered
            )
            
            # Validate equity percentage doesn't exceed 100%
            if equity_offered > 100.0:
                st.error("Equity offered cannot exceed 100%")
                st.session_state.equity_offered = 100.0  # Cap at 100%
            else:
                st.session_state.equity_offered = equity_offered
            
            # Pre-money Valuation with validation
            pre_money_valuation = st.number_input(
                "Valuation (Pre-money) (USD)", 
                min_value=0.0, 
                format="%.2f", 
                value=st.session_state.pre_money_valuation
            )

            # Validate pre-money valuation against funding amount
            if pre_money_valuation < st.session_state.funding_amount_requested and st.session_state.funding_amount_requested > 0:
                st.error("Pre-money valuation should be greater than the funding amount requested")
                # Don't update the state to prevent submission with invalid values
            else:
                st.session_state.pre_money_valuation = pre_money_valuation

            # Calculate Post-money Valuation automatically
            post_money_valuation = st.session_state.pre_money_valuation + st.session_state.funding_amount_requested
            st.markdown(f"**Post-money Valuation:** ${post_money_valuation:,.2f} USD")

            # Pitch deck uploader
            st.markdown("### 📄 Pitch Deck")
            if not st.session_state.pitch_deck_uploaded:
                uploaded_file = st.file_uploader("Upload Pitch Deck", type=["pdf"])
                if uploaded_file:
                    st.session_state.pitch_deck_file = uploaded_file

            # Investor selection
            st.markdown("### 👥 Potential Investors")
            # Cache investor options to prevent repeated API calls
            if "cached_investor_options" not in st.session_state:
                resp = requests.get(f"{FAST_API_URL}/fetch-investor-usernames")
                if resp.status_code == 200:
                    st.session_state.cached_investor_options = resp.json()
                else:
                    st.error("Could not load investor list.")
                    st.session_state.cached_investor_options = []
            
            investor_options = st.session_state.cached_investor_options

            # ensure session_state.investors is always a list
            if not isinstance(st.session_state.get("investors"), list):
                st.session_state.investors = []

            # filter any stale defaults
            valid_investor_defaults = [
                label for label in st.session_state.investors
                if label in investor_options
            ]

            # render
            selected_labels = st.multiselect(
                "Select Potential Investors",
                options=investor_options,
                default=valid_investor_defaults
            )

            # Save updated selection
            st.session_state.investors = selected_labels

            selected_usernames = [label.split(" (")[0] for label in selected_labels]

            # add a default for number of founders and their lists
            for key, default in {
                "founders_count": 1,
                "founder_names": [""],
                "founder_linkedin_urls": [""],
            }.items():
                st.session_state.setdefault(key, default)

            # after your other fields (valuation, industry, pitch deck, website, etc.)
            # ───── DYNAMIC FOUNDERS BLOCK ─────
            st.markdown("### 👥 Founders")

            # let user pick how many founders (up to 5 here)
            st.session_state.founders_count = st.number_input(
                "Select number of founders",
                min_value=1,
                max_value=5,
                step=1,
                value=st.session_state.founders_count,
                key="founders_count_input"
            )

            # make sure our lists are the right length
            count = st.session_state.founders_count
            names = st.session_state.founder_names
            links = st.session_state.founder_linkedin_urls

            if len(names) < count:
                names += [""] * (count - len(names))
            elif len(names) > count:
                names = names[:count]

            if len(links) < count:
                links += [""] * (count - len(links))
            elif len(links) > count:
                links = links[:count]

            st.session_state.founder_names = names
            st.session_state.founder_linkedin_urls = links

            # now render each pair of inputs
            for i in range(count):
                col_name, col_linkedin = st.columns([2, 3])
                st.session_state.founder_names[i] = col_name.text_input(
                    f"Founder #{i+1} Name",
                    value=st.session_state.founder_names[i],
                    key=f"founder_name_{i}"
                )
                
                # LinkedIn URL validation
                linkedin_url = col_linkedin.text_input(
                    f"Founder #{i+1} LinkedIn URL",
                    value=st.session_state.founder_linkedin_urls[i],
                    key=f"founder_linkedin_{i}"
                )
                if linkedin_url and not linkedin_url.startswith("https://www.linkedin.com/"):
                    col_linkedin.warning("Please enter a valid LinkedIn URL (https://www.linkedin.com/...)")
                st.session_state.founder_linkedin_urls[i] = linkedin_url

            # Handle submit
            if st.button("Submit"):
                missing = []
                validation_errors = []

                # core startup fields
                if not st.session_state.startup_name:
                    missing.append("Startup Name")
                if not st.session_state.email_address:
                    missing.append("Contact Email")
                if not st.session_state.funding_amount_requested:
                    missing.append("Funding Amount Requested")
                if not st.session_state.industry:
                    missing.append("Industry")
                if not st.session_state.pitch_deck_file:
                    missing.append("Pitch Deck Document")
                if not st.session_state.website_url:
                    missing.append("Website URL")

                # Validate equity percentage
                if st.session_state.equity_offered > 100.0:
                    validation_errors.append("Equity offered cannot exceed 100%")
                
                # Validate pre-money valuation
                if st.session_state.pre_money_valuation < st.session_state.funding_amount_requested:
                    validation_errors.append("Pre-money valuation must be greater than funding amount requested")

                # Proceed only if there are no validation errors
                if missing or validation_errors:
                    if missing:
                        st.error("⚠️ The following required fields are missing:")
                        for field in missing:
                            st.markdown(f"- ❌ **{field}**")
                    
                    if validation_errors:
                        st.error("⚠️ Please fix the following validation errors:")
                        for error in validation_errors:
                            st.markdown(f"- ❌ **{error}**")
                else:
                    try:
                        # First, check if startup already exists
                        check_response = requests.post(
                            f"{FAST_API_URL}/check-startup-exists",
                            json={"startup_name": st.session_state.startup_name}
                        )
                        
                        check_result = check_response.json()
                        
                        if check_result.get("exists"):
                            st.error(f"⚠️ {check_result.get('message')}. Please use a different name or contact support if this is your startup.")
                            return
                        
                        # Continue with submission if startup doesn't exist
                        founder_list = [
                            {
                                "startup_name": st.session_state.startup_name,
                                "founder_name": name,
                                "linkedin_url": url
                            }
                            for name, url in zip(
                                st.session_state.founder_names,
                                st.session_state.founder_linkedin_urls
                            )
                        ]
                        
                        # Save the startup info - with new funding fields
                        startup_response = requests.post(
                            f"{FAST_API_URL}/add-startup-info",
                            json={
                                "startup_name": st.session_state.startup_name,
                                "email_address": st.session_state.email_address,
                                "website_url": st.session_state.website_url,
                                "industry": st.session_state.industry,
                                "funding_amount_requested": st.session_state.funding_amount_requested,
                                "round_type": st.session_state.round_type,
                                "equity_offered": st.session_state.equity_offered,
                                "pre_money_valuation": st.session_state.pre_money_valuation,
                                "post_money_valuation": post_money_valuation,
                                "investor_usernames": selected_usernames,
                                "founder_list": founder_list
                            }
                        )
                        
                        # Show success message
                        st.success("✅ Your startup information has been submitted successfully! Our team or investors will reach out to you if there's a fit.")
                            
                        # Show success message immediately after /add-startup-info response
                        if startup_response.ok:
                            # Process the pitch deck file directly (no threading)
                            if st.session_state.pitch_deck_file:
                                try:
                                    # Prepare founder LinkedIn URLs
                                    linkedin_urls_json = json.dumps(st.session_state.founder_linkedin_urls)
                                    
                                    # Create form data for file upload with all funding-related information
                                    files = {"file": st.session_state.pitch_deck_file}
                                    form_data = {
                                        "startup_name": st.session_state.startup_name,
                                        "industry": st.session_state.industry,
                                        "linkedin_urls": linkedin_urls_json,
                                        "website_url": st.session_state.website_url,
                                        # Add funding-related information
                                        "funding_amount": str(st.session_state.funding_amount_requested),
                                        "round_type": st.session_state.round_type,
                                        "equity_offered": str(st.session_state.equity_offered),
                                        "pre_money_valuation": str(st.session_state.pre_money_valuation),
                                        "post_money_valuation": str(post_money_valuation)
                                    }
                                    
                                    # Direct API call
                                    pitch_response = requests.post(
                                        f"{FAST_API_URL}/process-pitch-deck",
                                        files=files,
                                        data=form_data
                                    )
                                    
                                    if pitch_response.status_code == 200:
                                        print(f"Pitch deck processed successfully for {st.session_state.startup_name}")
                                    else:
                                        print(f"Error processing pitch deck: {pitch_response.status_code} - {pitch_response.text}")
                                    
                                except Exception as e:
                                    print(f"Error processing pitch deck: {e}")
                            
                            
                            # Clear fields
                            # strings → ""
                            for key in ["startup_name", "email_address", "website_url", "industry", "round_type"]:
                                st.session_state[key] = ""
                            # floats → 0.0
                            for key in ["funding_amount_requested", "equity_offered", "pre_money_valuation"]:
                                st.session_state[key] = 0.0
                            # lists → empty or initial
                            st.session_state.investors = []
                            st.session_state.founders_count = 1
                            st.session_state.founder_names = [""]
                            st.session_state.founder_linkedin_urls = [""]
                            # pitch deck flags
                            st.session_state.pitch_deck_file = None
                            st.session_state.pitch_deck_uploaded = False
                        else:
                            st.error(f"❌ Error saving startup information: {startup_response.status_code} - {startup_response.text}")
                            return

                    except Exception as e:
                        st.error(f"❌ Error during submission: {e}")

        # -------- INVESTOR SECTION --------
        elif st.session_state.user_type == "Investor":
            st.markdown("---")
            st.markdown("### 💼 Investor Login / Signup")
            st.markdown("""
            Log in to explore the startup ecosystem or sign up to get started. Your dashboard gives you access to filtered startup data and pitch decks.
            """)

            # Ensure defaults are initialized
            for key, default in {
                "inv_first_name": "",
                "inv_last_name": "",
                "inv_username": "",
                "inv_email": "",
                "inv_password": "",
                "login_username": "",
                "login_password": ""
            }.items():
                st.session_state.setdefault(key, default)

            if not st.session_state.show_signup:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.button("Login"):
                    if username and password:
                        #response = investor_auth.login_investor(username, password)
                        response = requests.post(
                            f"{FAST_API_URL}/investor-login-auth", 
                            json={"username": username, "password": password}
                        )
                        result = response.json()
                        if result.get("status") == "success":
                            st.session_state.is_logged_in = True
                            st.session_state.username = result.get("username", "")
                            st.success(f"✅ Welcome, {st.session_state.username}!")

                            # Clear login fields
                            st.session_state.login_username = ""
                            st.session_state.login_password = ""

                            st.session_state.page = "investor_dashboard"
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
                    else:
                        st.error("⚠️ Enter both username and password.")
                
                st.markdown("Don't have an account?")
                if st.button("Go to Signup"):
                    st.session_state.show_signup = True
                    st.rerun()
            else:
                st.markdown("### 📝 Create Your Investor Account")

                st.session_state.inv_first_name = st.text_input("First Name", value=st.session_state.inv_first_name, key="inv_first_name_field")
                st.session_state.inv_last_name = st.text_input("Last Name", value=st.session_state.inv_last_name, key="inv_last_name_field")
                st.session_state.inv_username = st.text_input("Username", value=st.session_state.inv_username, key="inv_username_field")
                st.session_state.inv_email = st.text_input("Email", value=st.session_state.inv_email, key="inv_email_field")
                st.session_state.inv_password = st.text_input("Password", type="password", value=st.session_state.inv_password, key="inv_password_field")

                if st.button("Sign Up"):
                    if all([st.session_state.inv_first_name, st.session_state.inv_last_name,
                            st.session_state.inv_username, st.session_state.inv_email, st.session_state.inv_password]):
                        # response = investor_auth.signup_investor(
                        #     st.session_state.inv_first_name,
                        #     st.session_state.inv_last_name,
                        #     st.session_state.inv_username,
                        #     st.session_state.inv_email,
                        #     st.session_state.inv_password
                        # )

                        response = requests.post(f"{FAST_API_URL}/investor-signup-auth", 
                            json={"first_name": st.session_state.inv_first_name,
                                  "last_name": st.session_state.inv_last_name,
                                  "username": st.session_state.inv_username,
                                  "email": st.session_state.inv_email,
                                  "password": st.session_state.inv_password}
                        )

                        result = response.json()
                        if result["status"] == "success":
                            st.success("🎉 Account created! Please log in.")
                            # investorIntel_entity.insert_investor(
                            #     st.session_state.inv_first_name,
                            #     st.session_state.inv_last_name,
                            #     st.session_state.inv_email,
                            #     st.session_state.inv_username
                            # )
                            resp2 = requests.post(
                                f"{FAST_API_URL}/add-investor-info",
                                json={
                                    "first_name": st.session_state.inv_first_name,
                                    "last_name": st.session_state.inv_last_name,
                                    "email": st.session_state.inv_email,
                                    "username": st.session_state.inv_username
                                }
                            )
                            if resp2.ok:
                                st.success("✅ Account created successfully.")
                            else:
                                st.error(f"❌ Failed to create an investor account: HTTP {resp2.status_code}")


                            # Clear sign-up fields
                            for field in ["inv_first_name", "inv_last_name", "inv_username", "inv_email", "inv_password"]:
                                st.session_state[field] = ""

                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error(f"{result['message']}")
                    else:
                        st.error("⚠️ Fill out all fields.")

                if st.button("Back to Login"):
                    st.session_state.show_signup = False
                    st.rerun()
