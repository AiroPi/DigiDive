FROM python:3.11 as base
WORKDIR /app
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

FROM base as prod
COPY ./src ./
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "main:app"]

FROM base as dev
EXPOSE 5000
CMD ["flask", "--app", "main.py",  "--debug", "run", "-h", "0.0.0.0", "-p", "5000"]
