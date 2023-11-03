import requests
import streamlit as st
import os

# Base URL for the FastAPI backend
BASE_URL = "http://127.0.0.1:8000"

def register_user(username, password):
    payload = {"username": username, "password": password}
    response = requests.post(f"{BASE_URL}/register", data=payload)
    return response

def login_user(username, password):
    payload = {"username": username, "password": password}
    response = requests.post(f"{BASE_URL}/login", data=payload)
    return response

def getPDFnames():
    try:
        response = requests.get(f"{BASE_URL}/unique_pdf_names")
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        unique_pdf_names = response.json()
        return unique_pdf_names
    except requests.exceptions.RequestException as e:
        # Handle any errors that occur during the request
        print(e)
        return ["Error fetching PDF names"]

# Function to get query results from FastAPI
def get_query_results(query_string):
    data_payload = {"query": query_string}
    response = requests.post(f"{BASE_URL}/query_text", json=data_payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch results: {response.status_code} - {response.text}")
        return None

def get_query_results_filter(query_string, pdf_name):
    data_payload = {"query": query_string, "pdf_name": pdf_name}
    response = requests.post(f"{BASE_URL}/query_text_filtered", json=data_payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch results: {response.status_code} - {response.text}")
        return None

def main():
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.title("User Login")
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            response = login_user(username, password)
            if response.status_code == 200:
                st.success("Login successful")
                jwt_token = response.json().get("access_token")
                
                # Open a new page after successful login
                st.markdown('---')
                st.title("User Dashboard")
                st.subheader("JWT Access Token")
                st.write(f"Received JWT Token: {jwt_token}")

            else:
                st.error("Invalid credentials")
        
        unique_pdf_names = getPDFnames()
        options = ["Select All"] + unique_pdf_names
        pdf_name = st.radio('Select a PDF name', options, index=0)

        Question = st.text_input("Enter your query here:")

        if pdf_name == "Select All":
            submit = st.button("Search All")
            if submit:
                results = get_query_results(Question)
                if results is not None:
                    st.write(results)
        
        else:
            Filter = st.button("Filter Search")
            if Filter:
                results = get_query_results_filter(Question,pdf_name)
                if results is not None:
                    st.write(results)

    elif choice == "Register":
        st.title("User Registration")
        st.subheader("Register")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        if new_password == confirm_password:
            if st.button("Register"):
                response = register_user(new_username, new_password)
                if response.status_code == 200:
                    st.success(response.json().get("token_type"))
        else:
            st.error("Passwords do not match")

if __name__ == "__main__":
    main()