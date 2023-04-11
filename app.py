from flask import (Flask, request, jsonify, 
                   render_template, redirect, 
                   url_for, session, abort, make_response,
                   flash, send_from_directory)
import json
# import sqlite3
import pymysql
import jwt
from datetime import datetime, timedelta
from functools import wraps
import re
from flask_cors import CORS
from flask_mysqldb import MySQL, MySQLdb
from settings import MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, JWT_SECRET_KEY
import os
from werkzeug.utils import secure_filename
from flask import request

UPLOAD_FOLDER = 'upload/'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)

# limited to 16 megabytes
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config["MYSQL_USER"] = MYSQL_USER
app.config["MYSQL_PASSWORD"] = MYSQL_PASSWORD
app.config["MYSQL_DB"] = MYSQL_DB
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

db = MySQL(app)

from blueprint_auth import authentication

CORS(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

conn = pymysql.connect(
        host='localhost',
        user= MYSQL_USER, 
        password = MYSQL_PASSWORD,
        db=MYSQL_DB,
		cursorclass=pymysql.cursors.DictCursor
        )
cur = conn.cursor()

# Error Handling
@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404
	# return jsonify(error=str(e)), 404

@app.errorhandler(401)
def unauthorized(e):
	return render_template('401.html'), 401


# GET to get all the courses
# POST to create a new course
@app.route('/')
@app.route('/courses', methods=['GET', 'POST'])
def courses():
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("SELECT * FROM courses")
        courses = [
            dict(id=row['id'], prefixNumber=row['prefixNumber'], courseName=row['courseName'], units=row['units'])
            for row in cur.fetchall()
        ]
        if courses is not None:
            return jsonify(courses)
    
    if request.method == 'POST':
        new_prefixNumber = request.form['prefixNumber']
        new_courseName = request.form['courseName']
        new_units = request.form['units']
        cur.execute('INSERT INTO courses VALUES (NULL, % s, % s, % s)', (new_prefixNumber, new_courseName, new_units,))
        conn.commit()
        return f"Course with the id: {cur.lastrowid} created successfully", 201

# GET to get a single course by it's ID
# PUT to update an existing course
# DELETE to remove a course
@app.route('/course/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def single_course(id):
    course = None
    if request.method == 'GET':
        cur.execute("SELECT * FROM courses WHERE id=%s", (id,))
        rows = cur.fetchall()
        for r in rows:
            course = r
        if course is not None:
            return jsonify(course), 200
        else:
            return render_template('404.html'), 404
        
    if request.method == 'PUT':
        prefixNumber = request.form['prefixNumber']
        courseName = request.form['courseName']
        units = request.form['units']
        updated_course = {
            'id': id,
            'prefixNumber': prefixNumber,
            'courseName': courseName,
            'units': units
        }
        cur.execute('UPDATE courses SET prefixNumber =%s, courseName=%s, units=%s WHERE id=%s' , (prefixNumber, courseName, units, id))
        conn.commit()
        return jsonify(updated_course)
    if request.method == 'DELETE':
        cur.execute('DELETE FROM courses WHERE id=%s', (id,))
        conn.commit()
        return "The course with if: {} has been deleted.".format(id), 200

def allowed_file(filename):
     return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
           flash('No selected file')
           return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('download_file', name=filename))
    return '''
    <!doctype html>
    <title>Upload New File</title>
    <h1>Upload New File</h1>
    <form method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

app.register_blueprint(authentication, url_prefix="/auth")


if __name__ == '__main__':
    app.run(debug=True)