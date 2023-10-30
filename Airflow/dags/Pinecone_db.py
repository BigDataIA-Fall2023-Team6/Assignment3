import os
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from datetime import timedelta
import pinecone
import pandas as pd






def insert_data_to_pinecone(**kwargs):
    df = pd.read_csv('/opt/airflow/Embeddings/pdf_data.csv')  # Load the CSV data

    data = df.to_dict(orient='records')  # Convert DataFrame to a list of dictionaries

    # Create Pinecone index
    pinecone_index = pinecone.Index(index_name=PINECONE_INDEX_NAME)

    # Insert data into Pinecone
    pinecone_index.upsert(records=data)

# Function to create a new Pinecone index
def create_pinecone_index():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')

    pinecone.init(api_key=Pinecone_API_KEYS, environment='gcp-starter')
    PINECONE_INDEX_NAME = "OpenAI_Embeddings"
    try:
        pinecone.create_index("OpenAI_Embeddings",dimension=4096, metric="cosine")
        print(f"Created Pinecone index: {PINECONE_INDEX_NAME}")
    except pinecone.ApiException as e:
        if "already exists" in str(e):
            print(f"Pinecone index {PINECONE_INDEX_NAME} already exists.")
        else:
            raise e
        
dag = DAG(
    dag_id="pinecone_insertion_dag",
    schedule_interval=None,
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["pinecone_insertion"],
)

# Task to create a new Pinecone index
create_pinecone_index_task = PythonOperator(
    task_id="create_pinecone_index",
    python_callable=create_pinecone_index,
    dag=dag,
)

# Task to insert data into Pinecone
insert_to_pinecone_task = PythonOperator(
    task_id="insert_data_to_pinecone",
    python_callable=insert_data_to_pinecone,
    provide_context=True,
    dag=dag,
)

# Set task dependencies (ensure that the first DAG has completed before running this DAG)
create_pinecone_index_task >> insert_to_pinecone_task

