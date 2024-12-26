import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Team Availability Management System", layout="wide", page_icon="📅")

# File path for storing user data
USER_DATA_FILE = 'users.csv'

# Load user data from CSV file
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        return pd.read_csv(USER_DATA_FILE)
    else:
        return pd.DataFrame(columns=['username', 'password', 'role', 'team'])

def load_team_data():
    if os.path.exists(USER_DATA_FILE):
        df = pd.read_csv(USER_DATA_FILE)
        return df[df['role'] == 'Manager']
    else:
        return pd.DataFrame(columns=['username', 'password', 'role', 'team'])

# Save user data to CSV file
def save_user_data(users):
    users.to_csv(USER_DATA_FILE, index=False)

def check_duplicate_user(username):
    if username in users['username'].values:
        return True
    return False

def check_duplicate_record(availability, username, status, date):
    # check if there are any records with the same username, status, and date
    if not availability.empty:
        df = availability[(availability['Name'] == username) & (availability['Status'] == status) & (availability['Date'] == date)]
        if not df.empty:
            return True
    return False

# Initialize user data
users = load_user_data()

# Function to display login form in the sidebar
def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = authenticate(username, password)
        if user is not None:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.team = user['team']
            st.session_state.role = user['role']
            st.sidebar.success(f"Welcome {username}!")
        else:
            st.sidebar.error("Invalid username or password")

# Function to display registration form in the sidebar
def register():
    global users
    st.sidebar.title("Register")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    role = st.sidebar.selectbox("Role", ["Employee", "Manager"])
    team, emp_team = None, None
    if role == "Manager":
        team = st.sidebar.text_input("Team")
    if role == "Employee":
        user_df = load_team_data()
        options = user_df['team'].values
        emp_team = st.sidebar.selectbox("Team", options=options)
    if st.sidebar.button("Register"):
        if username in users['username'].values:
            st.sidebar.error("Username already exists")
        else:
            if role == "Manager":
                users.loc[len(users.index)] = [username, password, role, team]
            else:
                users.loc[len(users.index)] = [username, password, role, emp_team]
            save_user_data(users)
            st.sidebar.success("User registered successfully")

# Function to authenticate user
def authenticate(username, password):
    user = users[(users['username'] == username) & (users['password'] == password)]
    if not user.empty:
        return user.iloc[0]
    return None

def update_approval_status(selected_requests, status):
    availability = read_availability()
    for index in selected_requests:
        availability.loc[index, 'Approval Status'] = status
        availability.loc[index, 'MSGCount'] += 1
    availability.to_csv('availability.csv', index=False)

def admin_dashboard():
    st.title("Admin Dashboard")
    st.write("User Details")
    
    availability = read_availability()
    availability = availability[(availability['Approval Status'] == 'Pending') & (availability['Date'] >= str(pd.Timestamp.today().date()))]
    
    if not availability.empty:
        st.write("Approve or Reject Availability Requests")
        grouped = availability.groupby('Date')
        
        for date, group in grouped:
            st.subheader(f"Requests for {date}")
            with st.form(key=f'approval_form_{date}'):
                selected_requests = {}
                for index, row in group.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"Request from {row['Name']} for {row['Date']}")
                    with col2:
                        action = st.selectbox("Action", 
                                              options=["Pending", "Approve", "Reject"], 
                                              key=f"action_{index}")
                        selected_requests[index] = action
                
                submit_button = st.form_submit_button(label='Submit Selected Requests')
                
                if submit_button:
                    approve_requests = [index for index, action in selected_requests.items() if action == "Approve"]
                    reject_requests = [index for index, action in selected_requests.items() if action == "Reject"]
                    
                    if approve_requests:
                        update_approval_status(approve_requests, 'Approved')
                    if reject_requests:
                        update_approval_status(reject_requests, 'Rejected')
                    st.success(f"Requests for {date} have been processed")
    else:
        st.write("No pending requests to approve or reject")


    


def read_availability():
    if os.path.exists('availability.csv'):
        availability = pd.read_csv('availability.csv')
    else:
        availability = pd.DataFrame(columns=['Name', 'Status', 'Date', 'Approval Status', 'Team', 'MSGCount'])
    return availability

# Function to display user dashboard
def user_dashboard():
    st.title("User Dashboard")
    set_availability()

def disp_notifications(availability):
    notifications = availability[(availability['Name'] == st.session_state.username) & (availability['MSGCount'] > 0)]
    if not notifications.empty:
        # Display the notifications
        for index, row in notifications.iterrows():
            st.toast(f"Your request for {row['Date']} has been {row['Approval Status'].lower()}", icon = '🥳' if row['Approval Status'] == 'Approved' else '🥹')
            availability.loc[index, 'MSGCount'] = 0
        availability.to_csv('availability.csv', index=False)


def set_availability():
    availability = read_availability()
    disp_notifications(availability)
    
    insert, delete = st.columns(2)
    with insert:
        st.write("Set Availability")
        status = st.selectbox("Status", ['Floating', 'Leave', 'WFH'])
        start_date = st.date_input("Start Date", key='start_date')
        end_date = st.date_input("End Date", key='end_date')
        
        if st.button("Set Availability"):
            if start_date > end_date:
                st.error("Start date cannot be after end date.")
            else:
                availability = read_availability()  # Reload the DataFrame before insertion
                for single_date in pd.date_range(start=start_date, end=end_date):
                    date_str = str(single_date.date())
                    new_record = [st.session_state.username, status, date_str, 'Pending', st.session_state.team, 0]
                    
                    # Check for duplicates
                    if check_duplicate_record(availability, st.session_state.username, status, date_str):
                        st.error(f"Duplicate record found for {date_str}. Please try again.")
                    elif availability[(availability['Name'] == st.session_state.username) & (availability['Date'] == date_str)].shape[0] >= 1:
                        availability.loc[(availability['Name'] == st.session_state.username) & (availability['Date'] == date_str)] = new_record
                    else:
                        availability.loc[len(availability.index)] = new_record
                
                availability.to_csv('availability.csv', index=False)
                st.success("Availability set successfully")
    
    with delete:
        st.write("Delete Availability")
        date = str(st.date_input("Date", key='delete'))
        
        if st.button("Delete Availability"):
            availability = read_availability()  # Reload the DataFrame before deletion
            if availability[(availability['Name'] == st.session_state.username) & (availability['Date'] == date)].shape[0] == 0:
                st.error(f"No availability record found for {date}. Please try again.")
            else:
                availability = availability[~((availability['Name'] == st.session_state.username) & (availability['Date'] == date))]
                
                availability.to_csv('availability.csv', index=False)
                st.success("Availability deleted successfully")
        
    availability = availability[(availability['Name'] == st.session_state.username) & (availability['Date'] >= str(pd.Timestamp.today().date()))]
    # Display the records
    st.write("Your Availability Requests:")
    st.dataframe(availability[['Name', 'Status', 'Date', 'Approval Status']], hide_index=True, width=500)

# Main function to control the app flow
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        st.sidebar.title("Menu")
        st.sidebar.write(f"Welcome {st.session_state.username}!")
        st.sidebar.write(f"Team: {st.session_state.team}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.team = None
            st.session_state.role = None
            st.sidebar.success("Logged out successfully")
        else:
            if st.session_state.role == 'Manager':
                admin_dashboard()
            else:
                user_dashboard()
    else:
        option = st.sidebar.selectbox("Menu", ["Login", "Register"])
        if option == "Login":
            login()
        elif option == "Register":
            register()
        st.header("Team Availability Management System")
        availability = read_availability()
        c1_team, c2_date = st.columns(2)
        team, date = None, None
        with c1_team:
            st.write("Select team to view availability:")
            team = st.selectbox("Team", availability['Team'].unique(), key='team dashboard')
        with c2_date:
            st.write("Select date to view availability:")
            date = st.date_input("Date", key='date dashboard')
        available, offline = st.columns(2)
        users = load_user_data()
        users = users[(users['team'] == team) & (users['role'] == 'Employee')]
        working = pd.DataFrame(columns=['Name'])
        not_working = pd.DataFrame(columns=['Name'])
        wfh = pd.DataFrame(columns=['Name'])
        for index, row in users.iterrows():
            if availability[(availability['Name'] == row['username']) & (availability['Date'] == str(date)) & (availability['Status'] == 'WFH') & (availability['Approval Status'] == 'Approved')].shape[0] != 0:
                wfh.loc[len(wfh.index)] = row['username']
            elif availability[(availability['Name'] == row['username']) & (availability['Date'] == str(date)) & ((availability['Status'] == 'Leave') | (availability['Status'] == 'Floating')) & (availability['Approval Status'] == 'Approved')].shape[0] != 0:
                not_working.loc[len(not_working.index)] = row['username']
            else:
                working.loc[len(working.index)] = row['username']



        with available:
            st.write("<h2>Available:</h2>", unsafe_allow_html=True)
            st.write("----")
            names = working['Name'].values
            st.write("<h3>Working from office:</h3>", unsafe_allow_html=True)
            names_str = '\n'.join(names)
            if len(names) == 0:
                st.write("No one is working from office")
            else:
                st.text(names_str)
            st.write("<h3>Working from home:</h3>", unsafe_allow_html=True)
            names = wfh['Name'].values
            names_str = '\n'.join(names)
            if len(names) == 0:
                st.write("No one is working from home")
            else:
                st.text(names_str)
        with offline:
            st.write("<h2>Not Available:</h2>", unsafe_allow_html=True)
            st.write("----")
            names = not_working['Name'].values
            names_str = '\n'.join(names)
            if len(names) == 0:
                st.write("<h4>No one is on leave or floating</h4>", unsafe_allow_html=True)
            else:
                st.write("<h3>On leave or floating:</h3>", unsafe_allow_html=True)
                st.text(names_str)
        
        st.write("----")
        st.write("----")

  
    st.sidebar.title("Developer Profile")
    st.sidebar.info("""
        **Name:** Devendar Reddy M \n
        **GitHub:** [github.com/Devendar](https://github.com/Musalappagaridevendrareddy) \n
        **LinkedIn:** [linkedin.com/in/Devendar](https://www.linkedin.com/in/musalappagari-devendrareddy-drbu/) \n
        **Email:** devsobhaeswar143@gmail.com
    """)

if __name__ == "__main__":
    main()