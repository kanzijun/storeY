from flask import Flask, request, Response
import json

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

	db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
	cursor = db.cursor()
	cursor.execute("INSERT INTO stories VALUES (title, text, current_user, state);")
	db.commit()
	db.close()
		
	resp = Response(json.dumps({ "title": title }), status=201, mimetype='application/json')
	return resp
	

@app.route('/story/list', methods=["GET"])
def list_stories_titles():
	resp = Response(json.dumps(df['title'].to_dict()), status=200, mimetype='application/json')
	return resp

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
	
	try:
		db = MySQLdb.connect("mysql-server", "root", "secret", "mydb")
		cursor = db.cursor()
		cursor.execute("SELECT * FROM stories WHERE title = %s", (title))
		rows = cursor.fetchone()
		if (rows != None):
		data = {"title": rows[0], "text": rows[1], "current_user": rows[2], "state": rows[3]}
		db.close()

		resp = Response(json.dumps(data), status=200, mimetype='application/json')
		return resp

	except KeyError:
		data = { "error": "There is no story with that title." }
		resp = Response(json.dumps(data), status=404, mimetype='application/json')
		return resp


# @app.route('story/<title>/edit')

# @app.route('story/<title>/end')

# @app.route('story/<title>/leave')