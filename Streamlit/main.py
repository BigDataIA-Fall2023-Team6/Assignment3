import requests
import streamlit as st

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

def get_embeddings(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/embeddings", headers=headers)
    return response


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
                
                # Fetch and display the list of embeddings
                embeddings_response = get_embeddings(jwt_token)
                if embeddings_response.status_code == 200:
                    embeddings = embeddings_response.json()
                    selected_embedding = st.selectbox("Select Embedding", embeddings)
                    
                    # Input question related to the selected embedding
                    question = st.text_input("Ask a question")
                    st.button("Submit Query.")
                    # if st.button("Get Answer"):
                    #     answer_response = ask_question(jwt_token, selected_embedding, question)
                    #     if answer_response.status_code == 200:
                    #         answer = answer_response.json().get("answer")
                    #         st.write("Answer:", answer)
                    #     else:
                    #         st.error("Failed to get the answer.")
                else:
                    st.error("Failed to retrieve embeddings.")
            else:
                st.error("Invalid credentials")

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