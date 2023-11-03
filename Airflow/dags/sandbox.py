import os
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import openai
import requests
import PyPDF2
import pandas as pd
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.models import Variable

user_input ={
    "pdf_urls" : [
                "https://www.sec.gov/files/form1.pdf",
                "https://www.sec.gov/files/form10.pdf",
                "https://www.sec.gov/files/form11-k.pdf",
                "https://www.sec.gov/files/form8-a.pdf",
                "https://www.sec.gov/files/formn-54c.pdf"
            ]
}

class CustomPythonOperator(BaseOperator):
    @apply_defaults
    def __init__(self, python_callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.python_callable = python_callable

    def execute(self, context):
        return self.python_callable(context)
    
GPT_MODEL = "gpt-3.5-turbo"
api_key = os.getenv('OPENAI_KEY')  # Replace with your actual OpenAI API key
openai.api_key = api_key

def user_prompt(**kwargs):
    # Display a form to get user input for PDF URLs
    return input("Enter PDF URLs separated by commas: ").split(',')

def should_continue(**kwargs):
    user_input = kwargs['task_instance'].xcom_pull(task_ids='user_input_task')
    if user_input:
        return 'continue_task'
    return 'end_task'


def extract_text_from_pdfs(**kwargs):
    pdf_urls = kwargs["params"]["pdf_urls"]
    pdf_texts = [] 
    pdf_names = []# Initialize an empty list to store the extracted text
    for pdf_url in pdf_urls:
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()

            # Open the PDF file from the response content
            with open('temp.pdf', 'wb') as pdf_file:
                pdf_file.write(response.content)

            # Extract text from the PDF
            pdf_text = ""
            with open('temp.pdf', 'rb') as pdf_file:
                
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                pdf_names.append(pdf_url.split("/")[-1].split(".pdf")[0])
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    pdf_text += page.extract_text()
            print(f"Extracted texts from {pdf_url}",pdf_texts)
            pdf_texts.append(pdf_text)
            
        except Exception as e:
            print(f"Error extracting text from {pdf_url}: {str(e)}")
    # print(f"Extracted texts from {pdf_url}: {str(e)}",pdf_texts)
    return pdf_texts, pdf_names

def openai_embeddings(text, model="text-embedding-ada-002"):
    
    response = openai.Embedding.create(model=model, input=text)
    return response['data'][0]['embedding']

# def save_data_to_csv(**kwargs):
def generate_text_embeddings(**kwargs):
    pdf_texts, pdf_names =kwargs['ti'].xcom_pull(task_ids='extract_text_from_pdfs')
    
    print(pdf_texts)
    # Initialize data structures to store the data
    data = []

    # Process the extracted text, chunk it, and generate embeddings
    for i, text in enumerate(pdf_texts):
        print(f"Extracted texts:",pdf_texts)
        chunks = []
        current_chunk = ""
        current_length = 0
        max_chunk_length = 250
        for paragraph in text.split("\n"):
            if current_length + len(paragraph) <= max_chunk_length:
                current_chunk += paragraph + "\n"
                current_length += len(paragraph)
            else:
                chunks.append(current_chunk)
                current_chunk = paragraph + "\n"
                current_length = len(paragraph)
        if current_chunk:
            chunks.append(current_chunk)
        
        
                # Print chunks once for each PDF
        print(f"Chunks for PDF {i + 1}:", chunks)    
        text_chunks = chunks
        print(chunks)
        embeddings = [openai_embeddings(chunk) for chunk in text_chunks]
        
        # Store the data
        for j, chunk in enumerate(text_chunks):
            data.append({
                'PDF': i + 1,
                'PDF_Name': pdf_names[i],
                'Chunk_Number': j + 1,
                'Chunk_Text': chunk,
                'Embedding': embeddings[j]
            })

    # Create a DataFrame from the data
    df = pd.DataFrame(data)
    
    return df

def save_data_to_csv(**kwargs):
    df = kwargs['ti'].xcom_pull(task_ids='generate_embeddings_and_save_csv')  # Pull the DataFrame from a previous task
    csv_file_path = '/opt/airflow/Embeddings/pdf_data.csv'
    df.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")

dag = DAG(
    dag_id="pdf_processing_dag",
    schedule_interval=None,
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["pdf_processing"],
    params= {
            'pdf_urls': [
                "https://www.sec.gov/files/form1.pdf",
                "https://www.sec.gov/files/form10.pdf",
                "https://www.sec.gov/files/form11-k.pdf",
                "https://www.sec.gov/files/form8-a.pdf",
                "https://www.sec.gov/files/formn-54c.pdf"
            ]
        }
)

# Task for extracting text from PDFs
extract_text_task = PythonOperator(
    task_id="extract_text_from_pdfs",
    python_callable=extract_text_from_pdfs,
    # op_args=[pdf_urls],
    # op_kwargs={'pdf_urls': '{{ params.pdf_urls }}'},
    provide_context=True,
    dag=dag,
)
# pdf_texts=[]
# # Task for chunking the text
# chunk_text_task = PythonOperator(
#     task_id="chunk_text",
#     python_callable=chunk_text,
#     provide_context=True,
#     op_kwargs={
#         'text': "{{ ti.xcom_pull(key='pdf_texts', task_ids='extract_text_from_pdfs') }}",  # Pull the 'pdf_texts' variable from XCom
#         'max_chunk_length': 1200
#     },
#     dag=dag,
# )

# Task for generating embeddings and saving to CSV
generate_embeddings_task = PythonOperator(
    task_id="generate_embeddings_and_save_csv",
    python_callable=generate_text_embeddings,
    provide_context=True,
    dag=dag,
)

# Task for saving data to CSV
save_csv_task = PythonOperator(
    task_id="save_data_to_csv",
    python_callable=save_data_to_csv,
    provide_context=True,  # Include this to access the context and XCom
    dag=dag,
)

# Set task dependencies
extract_text_task >> generate_embeddings_task >> save_csv_task
