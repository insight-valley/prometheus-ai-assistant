FROM --platform=linux/amd64 python:3.9-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=${PYTHONPATH}:${PWD}

WORKDIR /app
RUN pip3 install poetry

COPY . /app/
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev
RUN playwright install
CMD python -m chainlit run app.py -h --host 0.0.0.0 --port ${PORT}
