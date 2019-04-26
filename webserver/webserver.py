from flask import Flask, request, Response, abort
import json
import logging
import random
import time

app = Flask(__name__)


import MySQLdb
from rq import Queue
from redis import Redis


q = Queue(connection=Redis(host="assignment2-redis", port=6379))
dictionary = {}


@app.route('/v1/tasks', methods=["GET"])
def print_all():
	tasks = []

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM tasks")
	rows = cursor.fetchall()
	for row in rows:
	    tasks.append(row)
	db.close()

	data = {"tasks": tasks}

	status_code = 200
	resp = Response(json.dumps(data), mimetype='application/json', status=status_code)
	return resp


@app.route('/v1/tasks', methods=["POST"])
def create_task():

	tasks = []
	id_val = 0


	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		title = arguments.get("title")
		is_completed = arguments.get("is_completed")
		recipient = arguments.get("notify")

		db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
		cursor = db.cursor()
		cursor.execute("SELECT * FROM tasks")
		cursor.execute("INSERT INTO tasks (task, is_completed, notify) VALUES (%s, %s, %s)", (title, is_completed, recipient))
		db.commit()
		id_val = cursor.lastrowid
		db.close()

	data = {"id": id_val}

	if is_completed == True:
		logging.info("Task '{}' has been completed and email sent out.".format(title))
		job = q.enqueue("workerserver.send_email", recipient, "Task Completed!", "Task '{}' was completed".format(title))


	status_code = 201
	resp = Response(json.dumps(data), mimetype='application/json', status=status_code)

	return resp
    


@app.route('/v1/tasks/<id>', methods=["GET"])
def get_task(id):

	data = {"error": "There is no task at that id"}
	id_val = int(id)
	flag = 0

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM tasks WHERE id = %s", (id_val,))
	rows = cursor.fetchone()
	if (rows != None):
		data = {"id": rows[0], "title": rows[1], "is_completed": rows[2], "notify": rows[3]}
	db.close()


	if flag == 0:
		status_code = 404
	else:
		status_code = 200
		

	

	resp = Response(json.dumps(data), mimetype='application/json', status=status_code)

	return resp



#/delete?
@app.route('/v1/tasks/<id>', methods=["DELETE"])
def delete(id):
	id_val = int(id)


	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("DELETE FROM tasks WHERE id = %s", (id_val,))
	db.commit()
	db.close()

			
	status_code = 204
	data = None
	resp = Response(data, mimetype='application/json', status=status_code)

	return resp

# UPdates an existing task
@app.route('/v1/tasks/<id>', methods=["PUT"])
def edit_task(id):
	id_val = int(id)
	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		title = arguments.get("title")
		is_completed = arguments.get("is_completed")
		recipient = arguments.get("notify")


		db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
		cursor = db.cursor()
		cursor.execute("UPDATE tasks SET task = %s, is_completed = %s, notify = %s WHERE id = %s", (title, is_completed, recipient, id_val))
		db.commit()
		db.close()

		if is_completed == True:
			logging.info("Task '{}' has been completed and email sent out.".format(title))
			job = q.enqueue("workerserver.send_email", recipient, "Task Completed!", "Task '{}' was completed".format(title))

	status_code = 204
	data = None
	resp = Response(data, mimetype='application/json', status=status_code)

	return resp



