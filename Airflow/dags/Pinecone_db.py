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


# Models a simple batch generator that make chunks out of an input DataFrame
# class BatchGenerator:
    
    
#     def __init__(self, batch_size: int = 10) -> None:
#         self.batch_size = batch_size
    
#     # Makes chunks out of an input DataFrame
#     def to_batches(self, df: pd.DataFrame) -> Iterator[pd.DataFrame]:
#         splits = self.splits_num(df.shape[0])
#         if splits <= 1:
#             yield df
#         else:
#             for chunk in np.array_split(df, splits):
#                 yield chunk

#     # Determines how many chunks DataFrame contains
#     def splits_num(self, elements: int) -> int:
#         return round(elements / self.batch_size)
    
#     __call__ = to_batches

# df_batcher = BatchGenerator(300)

def initialize_pineconedb():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")

def insert_data_to_pinecone(**kwargs):
    df = pd.read_csv('/opt/airflow/Embeddings/pdf_data.csv')
    
    df['Embedding'] = df.Embedding.apply(literal_eval)
    df['vector_id'] = range(len(df))
    PINECONE_INDEX_NAME = "openai-embeddings"
    data = df.to_dict(orient='records')  


    pinecone_index = pinecone.Index(index_name=PINECONE_INDEX_NAME)


    pinecone_index.upsert(records=data)


def create_pinecone_index():
    
    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')

    # pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    # PINECONE_INDEX_NAME = "OpenAI_Embeddings"
    # try:
    #     pinecone.create_index(PINECONE_INDEX_NAME,dimension=4096, metric="cosine")
    #     print(f"Created Pinecone index: {PINECONE_INDEX_NAME}")
    # except pinecone.ApiException as e:
    #     if "already exists" in str(e):
    #         print(f"Pinecone index {PINECONE_INDEX_NAME} already exists.")
    #     else:
    #         raise e

    Pinecone_API_KEYS = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=Pinecone_API_KEYS, environment="gcp-starter")
    index_name = 'openaiembeddings'


    if index_name in pinecone.list_indexes():
        pinecone.delete_index(index_name)
        

    pinecone.create_index(name='openaiembeddings', dimension = 4096, metric="cosine")
    
    
        
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

