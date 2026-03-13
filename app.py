import streamlit as st
import pandas as pd
import os

# Set page configuration
st.set_page_config(page_title="Secure Sales Dashboard", layout="wide")

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None

def check_password(username, password):
    """Checks whether a password entered by the user is correct."""
    
    # Define specific credentials and roles
    users = {
        "adel": {"password": "adel4040", "role": "admin"},
        "Karim": {"password": "Karim123", "role": "user"},
        "hisham": {"password": "hisham123", "role": "user"}
    }
    
    # Check if the username exists and password matches
    if username in users and users[username]["password"] == password:
        return True, users[username]["role"]
        
    return False, None

def login_page():
    """Displays the login form."""
    st.title("🔐 Login to Dashboard")
    st.write("Please enter your credentials to access the report.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username and password:
                is_valid, role = check_password(username, password)
                if is_valid:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = role
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please provide both username and password.")

def logout():
    """Handles user logout."""
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.session_state["username"] = None
    st.rerun()

def admin_panel():
    """Displays the admin file uploader."""
    st.header("🛠️ Admin Panel")
    st.info("Upload the latest `.xlsx` dataset to update the dashboard for everyone.")
    
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            # Try to read the file first to ensure it's a valid Excel format
            with st.spinner("Validating file..."):
                pd.read_excel(uploaded_file, nrows=10) # Just read top rows to validate
                
            # If successful, save it locally to be read by the dashboard
            with open("current_data.xlsx", "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.success("✅ File successfully uploaded and saved as `current_data.xlsx`!")
            
            # Clear the cache so the dashboard loads the newly uploaded data
            load_data.clear()
        except Exception as e:
            st.error(f"Error processing the file. Are you sure it's a valid Excel file? Details: {e}")
            
    st.divider()
    st.write("### Current Data Status")
    if os.path.exists("current_data.xlsx"):
        file_size = os.path.getsize("current_data.xlsx") / 1024 # KB
        st.write(f"✔️ `current_data.xlsx` is present ({file_size:.2f} KB).")
    else:
        st.warning("❌ `current_data.xlsx` has not been uploaded yet.")

@st.cache_data
def load_data(filepath):
    """Loads the Excel file. Uses st.cache_data for performance."""
    try:
        return pd.read_excel(filepath)
    except Exception as e:
        return None

def main_dashboard():
    """Displays the main analytics dashboard."""
    st.title("📊 Interactive Sales Dashboard")
    st.write("This dashboard analyzes the latest sales data.")
    
    data_path = "current_data.xlsx"
    
    # Check if the data file exists
    if not os.path.exists(data_path):
        st.warning("⚠️ The data file (`current_data.xlsx`) is missing. Please ask an Admin to upload the latest data.")
        return
        
    with st.spinner("Loading data..."):
        df = load_data(data_path)
        
    if df is None:
        st.error("Failed to load the Excel data. The file might be corrupted.")
        return
    if df.empty:
        st.warning("The uploaded Excel file is empty.")
        return
        
    # Strip any potential leading/trailing whitespaces in column names
    df.columns = df.columns.str.strip()
    
    # --- UI & FILTERING ---
    st.sidebar.header("Filters")
    
    if "SUBCATEGORY" in df.columns:
        # Get unique subcategories and drop missing strings
        subcategories = df["SUBCATEGORY"].dropna().unique().tolist()
        subcategories.sort()
        
        # Selectbox for filtering
        selected_subcategory = st.sidebar.selectbox("Select a Subcategory", subcategories)
        
        # Filter dataframe based on selection
        filtered_df = df[df["SUBCATEGORY"] == selected_subcategory]
    else:
        st.error("The column 'SUBCATEGORY' was not found in the uploaded data.")
        return
        
    st.header(f"Results for: {selected_subcategory}")

    # Optional view of raw data for current selection
    with st.expander("View Raw Filtered Data"):
        st.dataframe(filtered_df)

    # --- SUMMARY VIEW ---
    st.subheader("📝 Summary Table")
    
    # Ensure required columns are present
    summary_cols = ["ITEM", "UNIT OF MEASURE", "DELIVERED QUANTITY", "CUSTOMER"]
    missing_cols = [col for col in summary_cols if col not in filtered_df.columns]
    
    if missing_cols:
        st.error(f"Missing required columns for summary view: {', '.join(missing_cols)}")
    else:
        # Ensure DELIVERED QUANTITY is numeric to prevent aggregation errors
        filtered_df = filtered_df.copy()
        filtered_df["DELIVERED QUANTITY"] = pd.to_numeric(filtered_df["DELIVERED QUANTITY"], errors="coerce").fillna(0)
        
        # Group by ITEM and UNIT OF MEASURE
        summary_table = filtered_df.groupby(["ITEM", "UNIT OF MEASURE"]).agg(
            Total_Delivered_Quantity=('DELIVERED QUANTITY', 'sum'),
            Unique_Customers=('CUSTOMER', 'nunique')
        ).reset_index()
        
        summary_table = summary_table.rename(columns={
            "Total_Delivered_Quantity": "Total Delivered Quantity",
            "Unique_Customers": "Number of Unique Customers"
        })
        
        st.dataframe(summary_table, use_container_width=True, hide_index=True)

    # --- DETAILED VIEW ---
    st.subheader("🔍 Detailed View: Customer Breakdown")
    
    detailed_cols = ["ITEM", "CUSTOMER", "DELIVERED QUANTITY"]
    missing_detail_cols = [col for col in detailed_cols if col not in filtered_df.columns]
    
    if missing_detail_cols:
        st.error(f"Missing required columns for detailed view: {', '.join(missing_detail_cols)}")
    else:
        # Create a Pivot Table
        detailed_table = pd.pivot_table(
            filtered_df,
            values='DELIVERED QUANTITY',
            index=['ITEM', 'UNIT OF MEASURE'],
            columns='CUSTOMER',
            aggfunc='sum',
            fill_value=0
        )
        
        # Add a Total Quantity column summing across all customers
        detailed_table['Total Quantity (إجمالي الكمية)'] = detailed_table.sum(axis=1)
        
        # Reset index to make ITEM and UNIT OF MEASURE regular columns again for Streamlit display
        detailed_table = detailed_table.reset_index()
        
        st.dataframe(detailed_table, use_container_width=True, hide_index=True)


# --- ROUTING & APP LOGIC ---

# If user is not authenticated, show login page
if not st.session_state["authenticated"]:
    login_page()
else:
    # Sidebar User Profile and Navigation
    st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state['username']}")
    st.sidebar.markdown(f"🏷️ **Role:** {st.session_state['role'].capitalize()}")
    
    if st.sidebar.button("Logout"):
        logout()
        
    st.sidebar.divider()
    
    # Admin View
    if st.session_state["role"] == "admin":
        # Tabs let Admins upload data and also view the dashboard
        tab1, tab2 = st.tabs(["📊 Dashboard", "⚙️ Admin Panel"])
        with tab1:
            main_dashboard()
        with tab2:
            admin_panel()
            
    # Manager / User View
    else:
        # Users only see the dashboard
        main_dashboard()
