
FROM python:3.10-slim

WORKDIR /app

RUN mkdir -p data/embeddings

COPY rag-worker/requirements.txt .
COPY rag-worker/constraints.txt .
COPY ingest ./ingest

COPY rag-worker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]


RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt -c constraints.txt \
 && pip check

ENV PYTHONUNBUFFERED=1
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

COPY . .





