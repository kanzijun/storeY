from flask import Flask, request, Response
import json
from grammarbot import GrammarBotClient
import MySQLdb

app = Flask(__name__)


@app.route('/story/start', methods=["POST"])
def start_story():
	if request.headers['Content-Type'] == 'application/json':
		arguments = request.get_json()
		title = arguments.get("title")
		text = arguments.get("text")
		current_user = arguments.get("current_user")
		state = arguments.get("state")

		if check_grammar_bot(text)==True:
			db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
			cursor = db.cursor()
			cursor.execute("INSERT INTO stories VALUES (title, text, current_user, state);")
			cursor.execute("INSERT INTO ip VALUES (title, user);")
			db.commit()
			db.close()

			resp = Response(json.dumps({ "title": title }), status=201, mimetype='application/json')
			return resp

	resp = Response(json.dumps({ "Error in content." }), status=201, mimetype='application/json')
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
	
	cursor.execute("SELECT ip_addr FROM ip WHERE title = %s", (title,))
	users = cursor.fetchall()



@app.route('/story/<title>/end', methods=["DELETE"])
def end_story(title):
	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("DELETE FROM stories WHERE title = %s", (title,))
	db.commit()
	db.close()

	resp = Response(status=204, mimetype='application/json')
	return resp

# @app.route('/story/<title>/leave')


def check_grammar_bot(text):
	client = GrammarBotClient()
	res = client.check(text, 'en-US')
	if len(res.matches)==0:
		return True
	return False
