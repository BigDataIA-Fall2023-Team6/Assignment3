import streamlit as st
import requests
import os
 
from dotenv import load_dotenv
 
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
 
def getPDFnames(access_token):
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{BASE_URL}/unique_pdf_names", headers=headers)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        unique_pdf_names = response.json()
        return unique_pdf_names
    except requests.exceptions.RequestException as e:
        # Handle any errors that occur during the request
        print(e)
        return ["Error fetching PDF names"]
 
def get_query_results_filter(query_string, pdf_name, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    data_payload = {"query": query_string, "pdf_name": pdf_name, "Authorization": f"Bearer {access_token}"}
    response = requests.post(f"{BASE_URL}/query_text_filtered", json=data_payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch results: {response.status_code} - {response.text}")
        return None
 
# Function to get query results from FastAPI
def get_query_results(query_string, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    data_payload = {"query": query_string}
    response = requests.post(f"{BASE_URL}/query_text", json=data_payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch results: {response.status_code} - {response.text}")
        return None
   
def qA(access_token):
    st.title("User Dashboard")

    # Function to read unique PDF names
    def read_unique_pdf_names(file_path):
        with open(file_path, 'r') as file:
            return [line.strip() for line in file]

    # Path to the file where unique PDF names are stored
    file_path = '/opt/streamlit/outputs/unique_pdf_names.txt'  # Adjust path accordingly

    # Read the unique PDF names
    unique_pdf_names = read_unique_pdf_names(file_path)

    # unique_pdf_names = getPDFnames(access_token)
    options = ["Select All"] + unique_pdf_names
    pdf_name = st.radio('Select a PDF name', options, index=0)
 
    Question = st.text_input("Enter your query here:")
 
    if pdf_name == "Select All":
        submit = st.button("Search All")
        if submit:
            results = get_query_results(Question, access_token)
            if results is not None:
                st.write(results)
   
    else:
        Filter = st.button("Filter Search")
        if Filter:
            results = get_query_results_filter(Question,pdf_name, access_token)
            if results is not None:
                st.write(results)