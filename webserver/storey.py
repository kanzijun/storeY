from flask import Flask, request, Response
import json
from grammarbot import GrammarBotClient
import MySQLdb

from apscheduler.scheduler import Scheduler

app = Flask(__name__)

def time_out_user():
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()

	current_user = row[2]
	cursor.execute("SELECT * FROM stories;")
	rows = cursor.fetchall()
	for row in rows:
		#get current user
		cursor.execute("SELECT current_ip_addr FROM stories WHERE title = %s", (row[0],))
		current_user = cursor.fetchone()

		#get valid user
		cursor.execute("SELECT ip_addr FROM ip WHERE title = %s and ip_addr > %s ORDER BY ip_addr LIMIT 1;", (row[0], current_user))
		valid_user = cursor.fetchone()

		#update current user value to valid user
		cursor.execute("UPDATE stories SET current_ip_addr = %s WHERE title = %s", (valid_user, row[0]))
		db.commit()
		db.close()

sched = Scheduler(daemon=True)
sched.start()
sched.add_interval_job(time_out_user, minutes=10)

@app.route('/story/start', methods=["POST"])
def start_story():

	user_ip = request.remote_addr

	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		title = arguments.get("title")
		text = arguments.get("text")

		if check_grammar_bot(text)==True:
			db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
			cursor = db.cursor()
			cursor.execute("INSERT INTO stories (title, text, current_ip_addr, state) VALUES (%s, %s, %s, %s)", (title, text, user_ip, 1))
			cursor.execute("INSERT INTO ip (title, ip_addr) VALUES (%s, %s)", (title, user_ip))
			db.commit()
			db.close()

			data = {"title": title}

			resp = Response(json.dumps(data), mimetype='application/json', status=201)
			return resp

	data = {"Error" : "Error in content type"}

	resp = Response(json.dumps(data), status=201, mimetype='application/json')
	return resp


@app.route('/story/list', methods=["GET"])
def list_stories_titles():

	stories = []

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM stories")
	rows = cursor.fetchall()
	for row in rows:
	    stories.append(row)
	db.close()

	data = {"stories": stories}

	resp = Response(json.dumps(data), status=200, mimetype='application/json')
	return resp

@app.route('/story/<title>', methods=["GET"])
def display_story(title):


	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	rows = cursor.fetchone()
	if (rows != None):
		data = {"title": rows[0], "text": rows[1], "current_user": rows[2], "state": rows[3]}
		db.close()
		resp = Response(json.dumps(data), status=200, mimetype='application/json')
		return resp

	data = { "Error": "There is no story with that title." }
	resp = Response(json.dumps(data), status=404, mimetype='application/json')
	return resp


@app.route('/story/<title>/edit', methods=["PUT"])
def edit_story(title):

	user_ip = request.remote_addr

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	#if user is new to story, add user to table ip
	cursor.execute("INSERT INTO ip SELECT * FROM (SELECT %s, %s) AS tmp WHERE NOT EXISTS (SELECT * FROM ip WHERE title = %s and ip_addr = %s) LIMIT 1;", (title, user_ip, title, user_ip))

	#get list of users writing title
	cursor.execute("SELECT ip_addr FROM ip WHERE title = %s", (title,))
	users = cursor.fetchall()

	#get valid user
	cursor.execute("SELECT ip_addr FROM ip  WHERE title = %s and ip_addr > %s ORDER BY ip_addr LIMIT 1;", (title, current_user))
	valid_user = cursor.fetchone()

	if user_ip == valid_user:

		if request.headers['Content-Type'] == 'application/json':
			arguments = request.get_json()
			new_text = arguments.get("new_text")

			if check_grammar_bot(new_text)==True:

				db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
				cursor = db.cursor()
				cursor.execute("SELECT text FROM stories WHERE title = %s;", (title,))
				old_text = cursor.fetchone()
				updated_text = old_text + new_text
				cursor.execute("UPDATE stories SET text = %s WHERE title = %s;", (updated_text, title))
				db.commit()
				db.close()

				resp = Response(status=204, mimetype='application/json')
				return resp

	data = { "Error": "It is not your turn." }
	resp = Response(json.dumps(data), status=200, mimetype='application/json')
	return resp


@app.route('/story/<title>/end', methods=["PUT"])
def end_story(title):
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("UPDATE stories SET state = 0 WHERE title = %s", (title,))
	db.commit()
	db.close()

	resp = Response(status=204, mimetype='application/json')
	return resp

@app.route('/story/<title>/leave', methods=["DELETE"])
def leave_story(title):

	user_ip = request.remote_addr

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("DELETE FROM ip WHERE title = %s and ip_addr = %s;", (title, user_ip))
	db.commit()
	db.close()

	resp = Response(status=204, mimetype='application/json')
	return resp


def check_grammar_bot(text):
	client = GrammarBotClient()
	res = client.check(text, 'en-US')
	if len(res.matches)==0:
		return True
	return False