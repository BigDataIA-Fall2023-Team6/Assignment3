import os
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from datetime import timedelta
import pinecone
import pandas as pd
from ast import literal_eval
from typing import List, Iterator
import numpy as np




def initialize_pineconedb():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")

def insert_data_to_pinecone(**kwargs):
# Read the CSV file into a Pandas DataFrame

    df = pd.read_csv('/opt/airflow/Embeddings/pdf_data.csv')
    # embedding = literal_eval(row['Embedding'])
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    index_name = 'openaiembeddings00'
    index = pinecone.Index(index_name=index_name)

    
    from ast import literal_eval
    # Create a Pinecone index
    index = pinecone.Index(index_name=index_name)

    records = []

    for _, row in df.iterrows():
        # Convert the 'Embedding' string to a list
        embedding = literal_eval(row['Embedding'])

        # Create a dictionary with the 'metadata' field
        record = {
            'id': str(_),  # Unique ID
            'values': embedding,  # Embedding as a list of floats
            'metadata': {
                'PDF': row['PDF'],
                'PDF_Name': row['PDF_Name'],
                'Chunk_Number': row['Chunk_Number'],
                'Chunk_Text': row['Chunk_Text']
            }
        }

        records.append(record)  # Append the record to the 'records' list

    # Upsert the records into the index
    index.upsert(vectors=records)



def create_pinecone_index():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    index_name = 'openaiembeddings00'
    if index_name in pinecone.list_indexes():
        pinecone.delete_index(index_name)
        

    pinecone.create_index(name=index_name, dimension = 1536, metric="cosine")
    
    
        
dag = DAG(
    dag_id="pinecone_insertion_dag",
    schedule_interval=None,
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["pinecone_insertion"],
)

initialize_pinecone_vectordb_task = PythonOperator(
    task_id="init_pinecone_db",
    python_callable= initialize_pineconedb,
    dag=dag,
)


create_pinecone_index_task = PythonOperator(
    task_id="create_pinecone_index",
    python_callable=create_pinecone_index,
    provide_context=True,
    dag=dag,
)


insert_to_pinecone_task = PythonOperator(
    task_id="insert_data_to_pinecone",
    python_callable=insert_data_to_pinecone,
    provide_context=True,
    dag=dag,
)


initialize_pinecone_vectordb_task >> create_pinecone_index_task >> insert_to_pinecone_task

