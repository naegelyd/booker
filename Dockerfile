FROM python:3.11-slim

WORKDIR /booker

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

CMD ["uvicorn", "booker.main:app", "--host", "0.0.0.0", "--port", "8000"]