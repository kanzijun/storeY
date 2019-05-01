FROM python:3
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install mysqlclient
RUN pip install grammarbot
EXPOSE 5000
ENTRYPOINT ["flask"]
CMD ["run", "--host=0.0.0.0"]
