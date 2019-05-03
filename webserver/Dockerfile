FROM python:3
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install mysqlclient
RUN pip install grammarbot
RUN pip install apscheduler==2.1.2
EXPOSE 5000
ENTRYPOINT ["flask"]
CMD ["run", "--host=0.0.0.0"]
