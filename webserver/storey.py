from flask import Flask, request, Response
import json
from grammarbot import GrammarBotClient
import MySQLdb

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

#start the scheduler
sched = BackgroundScheduler(daemon=True)
sched.start()

#add a job in the scheduler for each story that exists and is open (state 0)
db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
cursor = db.cursor()

cursor.execute("SELECT * FROM stories WHERE state = 1;")
stories = cursor.fetchall()

for story in stories:
	title = story[0]
	sched.add_job(lambda: time_out_user(title), 'interval', minutes=1, id=title)

db.close()

def time_out_user(title):
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()

	query = "SELECT * FROM stories WHERE title = '{}';".format(title)
	cursor.execute(query)
	row = cursor.fetchone()

	#get current user
	cursor.execute("SELECT current_ip_addr FROM stories WHERE title = %s;", (row[0],))
	current_user = cursor.fetchone()[0]

	query = "SELECT id from ip WHERE title = '{}' AND ip_addr = '{}';".format(row[0], current_user)
	cursor.execute(query)
	current_id = cursor.fetchone()[0]

	query = query = "SELECT ip_addr from ip WHERE title = '{}' AND id > {} ORDER BY id LIMIT 1;".format(row[0], current_id)
	cursor.execute(query)
	next_ip = cursor.fetchone()

	if not next_ip:
		query = "SELECT ip_addr from ip WHERE id = (SELECT MIN(id) from ip WHERE title = '{}');".format(row[0])
		cursor.execute(query)
		next_ip = cursor.fetchone()

	query = "UPDATE stories SET current_ip_addr = '{}' WHERE title = '{}';".format(next_ip[0], row[0])
	cursor.execute(query)

	print(next_ip[0] + " it's your turn for story " + title + "! Hurry you have 60 seconds!")

	db.commit()
	db.close()

@app.route('/story/start', methods=["POST"])
def start_story():
	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		user_ip = arguments.get("user")
		title = arguments.get("title")
		text = arguments.get("text")

		if check_grammar_bot(text)==True:
			db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
			cursor = db.cursor()

			#make sure the story title is unique
			query = "SELECT * from stories WHERE title = '{}';".format(title)
			cursor.execute(query)
			result = cursor.fetchone()

			#if there is already a story with this name, don't create the story
			if result:
				data = {"Error" : "Please enter a unique story title!"}
				resp = Response(json.dumps(data), mimetype='application/json', status=201)
				return resp

			cursor.execute("INSERT INTO stories (title, text, current_ip_addr, state) VALUES (%s, %s, %s, %s)", (title, text, user_ip, 1))
			cursor.execute("INSERT INTO ip (title, ip_addr) VALUES (%s, %s)", (title, user_ip))
			db.commit()
			db.close()

			data = {"title": title, "text": text}

			sched.add_job(lambda: time_out_user(title), 'interval', minutes=1, id=title)

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
	state = cursor.fetchone()[0]
	if state == 0:
		data = { "Error": "Story has ended." }
		resp = Response(json.dumps(data), status=200, mimetype='application/json')
		return resp

	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		user_ip = arguments.get("user")
	else:
		return "Must be json", 400

	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	#if there's only one user, and its the same user trying to edit the story, don't allow
	cursor.execute("SELECT COUNT(*) FROM ip WHERE title=%s", (title,))
	row = cursor.fetchone()
	user_count = row[0]
	if user_count == 1:
		if user_ip == current_user:
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

	#get updated current_user
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	if user_ip == current_user:
		# if request.headers['Content-Type'] == 'application/json':
		new_text = arguments.get("new_text")

		if check_grammar_bot(new_text)==True:
			db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
			cursor = db.cursor()
			cursor.execute("SELECT text FROM stories WHERE title = %s;", (title,))
			text_row = cursor.fetchone()
			old_text = text_row[0]
			updated_text = old_text + " " + new_text
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
	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		user_ip = arguments.get("user")
	else:
		return "Must be json", 400

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()

	#get updated current_user
	cursor.execute("SELECT * FROM stories WHERE title = %s", (title,))
	row = cursor.fetchone()
	current_user = row[2]

	#if it is the current user's turn they can end the story, otherwise send an error
	if user_ip == current_user:
		#if state of story is 0, story is already ended
		cursor.execute("SELECT state FROM stories WHERE title = %s", (title,))
		state = cursor.fetchone()[0]
		if state == 0:
			data = { "Error": "Story has already ended." }
			resp = Response(json.dumps(data), status=200, mimetype='application/json')
			return resp

		#else end the story
		cursor.execute("UPDATE stories SET state = 0 WHERE title = %s", (title,))
		db.commit()
		db.close()

		#stop scheduler from running for this story
		sched.remove_job(title)

		resp = Response(status=204, mimetype='application/json')
		return resp

	data = { "Error": "It is not your turn." }
	resp = Response(json.dumps(data), status=200, mimetype='application/json')

	return resp

@app.route('/story/<title>/leave', methods=["DELETE"])
def leave_story(title):
	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		user_ip = arguments.get("user")

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

		query = "SELECT ip_addr from ip WHERE title = '{}' AND id > {} ORDER BY id LIMIT 1;".format(title, current_id)
		cursor.execute(query)
		next_ip = cursor.fetchone()[0]

		if not next_ip:
			query = "SELECT ip_addr from ip WHERE title = '{}' AND id = min(id)".format(title)
			cursor.execute(query)
			next_ip = cursor.fetchone()[0]

		query = "UPDATE stories SET current_ip_addr = '{}' WHERE title = '{}'".format(next_ip, title)
		cursor.execute(query)
		db.commit()
	elif num_users == 1:
		query = "UPDATE stories SET state = 0 WHERE title = '{}';".format(title)
		cursor.execute(query)
		db.commit()

		#stop scheduler from running for this story
		sched.remove_job(title)

	#delete the user from the ip table
	query = "DELETE FROM ip WHERE title = '{}' and ip_addr = '{}';".format(title, user_ip)
	cursor.execute(query)
	db.commit()

	print(user_ip + " has left the story " + title)

	db.close()

	resp = Response(status=204, mimetype='application/json')
	return resp


def check_grammar_bot(text):
	client = GrammarBotClient()
	res = client.check(text, 'en-US')
	if len(res.matches)==0:
		return True
	return False
