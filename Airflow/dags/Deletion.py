import os
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from datetime import timedelta
import pinecone
import pandas as pd

user_input ={
    "index_name" : ["openaiembeddings00"]
}

def initialize_pineconedb():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    
# **kwargs
def delete_pinecone_index(**kwargs):
    index_name_list = kwargs["params"]["index_name"]
    
    if index_name_list:
        # Convert the selected element to a string
        index_name = str(index_name_list[0])
    # index_name = "openaiembeddings00"
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    # index_name = 'openaiembeddings00'
    index = pinecone.Index(index_name=index_name)
    
    df = pd.read_csv('/opt/airflow/Embeddings/pdf_data.csv')
    
    ids = [str(i) for i in range(0,len(df))]
    
   
    # index.delete(str(ids))
    # stats = index.describe_index_stats()
    # total_vector_count = stats['total_vector_count']
    
    # ids = [str(i) for i in range(0, total_vector_count)]
    
    for vector_ids in ids:
    # id =  "2"
        index.delete(str(vector_ids))
    
    return None
    
 
    
dag = DAG(
    dag_id="pinecone_index_deletion_dag",
    schedule_interval=None,
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["pinecone_index_deletion"],
    params=user_input
    # params= {
    # "index_name" : [
    #             "openaiembeddings00"
    #         ]
    #     }
)

initialize_pinecone_vectordb_task = PythonOperator(
    task_id="init_pinecone_db",
    python_callable= initialize_pineconedb,
    dag=dag,
)

delete_pinecone_index_task = PythonOperator(
    task_id="delete_pinecone_index",
    python_callable=delete_pinecone_index,
    provide_context=True,
    dag=dag,
)

initialize_pinecone_vectordb_task >> delete_pinecone_index_task
