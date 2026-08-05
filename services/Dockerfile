FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

WORKDIR /workspace/services/api

RUN pip install --no-cache-dir uv

COPY api/requirements.txt /workspace/services/api/requirements.txt
RUN uv pip install --system -r /workspace/services/api/requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/workspace/services/api"]
