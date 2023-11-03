FROM python:3.10.12 
# Enter your own python Environment

WORKDIR  /app

COPY requirements.txt ./

RUN pip install -r requirements.txt
RUN pip install uvicorn gunicorn 


COPY main.py ./

# copy Pipfile Pipfile.lock ./

# RUN pipenv install --system --deploy --ignore-pipfile

EXPOSE 8000

CMD [ "gunicorn","-w", "4","-k","uvicorn.workers.UvicornWorker","-b","0.0.0.0:8000", "main:app" ]