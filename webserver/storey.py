from flask import Flask, request, Response
import json
from grammarbot import GrammarBotClient
import MySQLdb

from apscheduler.scheduler import Scheduler

app = Flask(__name__)

def time_out_user():
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()

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

	user_ip = request.environ["REMOTE_ADDR"]
	#user_ip = request.remote_addr

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

	#if state of story is 0, don't allow user to edit story
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT state FROM stories WHERE title = %s", (title,))
	state = cursor.fetchone()
	if state == 0:
		data = { "Error": "Story has ended." }
		resp = Response(json.dumps(data), status=200, mimetype='application/json')
		return resp

	user_ip = request.remote_addr

	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	#if there's only one user, and its the same user trying to edit the story, don't allow
	cursor.execute("SELECT COUNT(*) FROM ip WHERE title=%s", (title,))
	row = cursor.fetchone()
	user_count = row[0]
	print("COUNT")
	print(user_count)
	if user_count == 1:
		print("FIRST HELLO")
		if user_ip == current_user:
			print("SECOND HELLO")
			db.close()
			data = { "Error": "It is not your turn, waiting for more users to join the story." }
			resp = Response(json.dumps(data), status=200, mimetype='application/json')
			return resp
		else:
			#if there's only one user, and its a new user joining, make new user the current user
			cursor.execute("INSERT INTO ip (title, ip_addr) VALUES (%s, %s)", (title, user_ip)) #add new_user to ip table
			cursor.execute("UPDATE stories SET current_ip_addr = %s WHERE title = %s", (user_ip, title)) #change current_user to new_user
			db.commit()

	#if user is new to story, add user to table ip
	cursor.execute("INSERT INTO ip (title, ip_addr) SELECT %s, %s WHERE NOT EXISTS (SELECT 1 FROM ip WHERE title=%s and ip_addr=%s);", (title, user_ip, title, user_ip))
	db.commit()
	# cursor.execute("INSERT INTO ip (title, ip_addr) SELECT * FROM (SELECT %s, %s) AS tmp WHERE NOT EXISTS (SELECT * FROM ip WHERE title = %s and ip_addr = %s) LIMIT 1;", (title, user_ip, title, user_ip))

	# #get list of users writing title
	# cursor.execute("SELECT ip_addr FROM ip WHERE title = %s", (title,))
	# users = cursor.fetchall()

	# #get valid user
	# cursor.execute("SELECT ip_addr FROM stories WHERE title = %s and ip_addr > %s ORDER BY ip_addr LIMIT 1;", (title, current_user))
	# cursor.execute("SELECT ip_addr FROM ip  WHERE title = %s and ip_addr > %s ORDER BY ip_addr LIMIT 1;", (title, current_user))
	# valid_user = cursor.fetchone()

	#get updated current_user
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	if user_ip == current_user:

		if request.headers['Content-Type'] == 'application/json':
			arguments = request.get_json()
			new_text = arguments.get("new_text")

			if check_grammar_bot(new_text)==True:

				db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
				cursor = db.cursor()
				cursor.execute("SELECT text FROM stories WHERE title = %s;", (title,))
				text_row = cursor.fetchone()
				old_text = text_row[0]
				updated_text = old_text + new_text
				cursor.execute("UPDATE stories SET text = %s WHERE title = %s;", (updated_text, title))
				db.commit()
				db.close()

				resp = Response(status=204, mimetype='application/json')
				return resp

	data = { "Error": "It is not your turn." }
	resp = Response(json.dumps(data), status=200, mimetype='application/json')
	return resp

@app.route('/story/<title>/users', methods=["GET"])
def get_users(title):

	users = []

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT ip_addr FROM ip WHERE title = %s", (title,))
	rows = cursor.fetchall()
	for row in rows:
	    users.append(row)
	db.close()

	data = {"Users": users}

	resp = Response(json.dumps(data), status=200, mimetype='application/json')
	return resp


@app.route('/story/<title>/end', methods=["PUT"])
def end_story(title):
	#if state of story is 0, story is already ended
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("SELECT state FROM stories WHERE title = %s", (title,))
	state = cursor.fetchone()
	if state == 0:
		data = { "Error": "Story has already ended." }
		resp = Response(json.dumps(data), status=200, mimetype='application/json')
		return resp

	user_ip = request.remote_addr

	#get updated current_user
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	if user_ip == current_user:


		db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
		cursor = db.cursor()
		cursor.execute("UPDATE stories SET state = 0 WHERE title = %s", (title,))
		db.commit()
		db.close()

		resp = Response(status=204, mimetype='application/json')
		return resp

	data = { "Error": "It is not your turn." }
	resp = Response(json.dumps(data), status=200, mimetype='application/json')
	return resp

@app.route('/story/leave/<title>', methods=["DELETE"])
def leave_story(title):

	user_ip = request.remote_addr

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()

	#get the number of users writing this story
	query = "SELECT COUNT(ip_addr) from ip WHERE title = '{}';".format(title)
	cursor.execute(query)
	num_users = int(cursor.fetchone()[0])

	#get the current user of this story
	query = "SELECT current_ip_addr from stories WHERE title = '{}';".format(title)
	cursor.execute(query)
	current_user = cursor.fetchone()[0]

	#close the story if you are the only user, else move the current user onto the next ip_addr if you are the current user
	if num_users > 1 and current_user == user_ip:
		query = "SELECT id from ip WHERE title = '{}' AND ip_addr = '{}';".format(title, user_ip)
		cursor.execute(query)
		current_id = cursor.fetchone()[0]

		query = "SELECT ip_addr from ip WHERE id > {} ORDER BY id LIMIT 1;".format(current_id)
		cursor.execute(query)
		next_ip = cursor.fetchone()[0]

		query = "UPDATE stories SET current_ip_addr = '{}' WHERE title = '{}'".format(next_ip, title)
		cursor.execute(query)
		db.commit()
	elif num_users == 1:
		query = "UPDATE stories SET state = 0 WHERE title = '{}';".format(title)
		cursor.execute(query)
		db.commit()

	#delete the user from the ip table
	query = "DELETE FROM ip WHERE title = '{}' and ip_addr = '{}';".format(title, user_ip)
	cursor.execute(query)
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
