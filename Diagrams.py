from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.azure.compute import BatchAccounts
from diagrams.onprem.workflow import Airflow
from diagrams.gcp.database import Firestore
from diagrams.programming.language import Python
from diagrams.aws.cost import CostAndUsageReport
from diagrams.programming.framework import FastAPI
from diagrams.aws.database import RDSPostgresqlInstance

with Diagram("Architecture Flow Diagram", show=False):

    with Cluster("Secure login User Session state for 30 mins", direction="TB"):
        user = User("User")
        python_ui = Python("Python UI (Streamlit)")
        aws_postgres = RDSPostgresqlInstance("AWS Postgres")

        Edge(label="Login and Registration") >> user >> python_ui
        python_ui >> aws_postgres
        aws_postgres >> python_ui

    airflow = Airflow("Airflow")
    pinecone = Firestore("Pinecone Database")

    # Create a custom "Local Directory" symbol
    Airflow_local_directory = BatchAccounts("Airflow Local Directory")

    # Connect "Airflow" to "Local Directory" with an arrow labeled "Saving CSV file"
    Edge(label="Saving CSV file") >> airflow >> Airflow_local_directory
    Airflow_local_directory >> airflow
    # Flow 2: User > Python UI > FastAPI > Database (Pinecone)
    with Cluster("Streamlit and Pinecone communication via FastAPI", direction="TB"):
        fastapi = FastAPI("FastAPI")
        python_ui - fastapi
        python_ui >> fastapi
        fastapi >> pinecone
        pinecone_api = pinecone
        pinecone_api >> python_ui

    # Flow 1: User > Airflow > Database (Pinecone)
    with Cluster("User > Airflow > Pinecone", direction="TB"):
        Edge(label="Execute the Airflow pipelines for processing the pdf urls                             ") >> user >> airflow >> pinecone
