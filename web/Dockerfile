FROM python:3.12 as base
WORKDIR /app
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

FROM base as prod
COPY ./src ./
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as dev
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
