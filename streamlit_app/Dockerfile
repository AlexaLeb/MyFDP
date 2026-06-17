FROM python:3.10-slim

WORKDIR /ui

COPY requirements.txt /ui/
RUN pip install --upgrade pip && pip install -r /ui/requirements.txt

COPY ./ /ui

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
