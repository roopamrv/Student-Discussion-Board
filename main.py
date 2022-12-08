from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
import requests
import json

app = Flask(__name__)
app.secret_key = 'your secret key'

if os.environ.get('GAE_ENV') == 'standard':
    app.config['MYSQL_UNIX_SOCKET'] = '/cloudsql/{}'.format(os.environ.get('CLOUD_SQL_CONNECTION_NAME'))

else:
    app.config['MYSQL_HOST'] = 'localhost'
    
app.config['MYSQL_USER'] = os.environ.get('CLOUD_SQL_USERNAME')
app.config['MYSQL_PASSWORD'] = os.environ.get('CLOUD_SQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('CLOUD_SQL_DATABASE_NAME')

stop_words={'ourselves', 'hers', 'between', 'yourself', 'but', 'again', 'there', 'about', 'once', 'during', 'out', 'very', 'having', 'with', 'they', 'own', 'an', 'be', 'some', 'for', 'do', 'its', 'yours', 'such', 'into', 'of', 'most', 'itself', 'other', 'off', 'is', 's', 'am', 'or', 'who', 'as', 'from', 'him', 'each', 'the', 'themselves', 'until', 'below', 'are', 'we', 'these', 'your', 'his', 'through', 'don', 'nor', 'me', 'were', 'her', 'more', 'himself', 'this', 'down', 'should', 'our', 'their', 'while', 'above', 'both', 'up', 'to', 'ours', 'had', 'she', 'all', 'no', 'when', 'at', 'any', 'before', 'them', 'same', 'and', 'been', 'have', 'in', 'will', 'on', 'does', 'yourselves', 'then', 'that', 'because', 'what', 'over', 'why', 'so', 'can', 'did', 'not', 'now', 'under', 'he', 'you', 'herself', 'has', 'just', 'where', 'too', 'only', 'myself', 'which', 'those', 'i', 'after', 'few', 'whom', 't', 'being', 'if', 'theirs', 'my', 'against', 'a', 'by', 'doing', 'it', 'how', 'further', 'was', 'here', 'than'}

mysql = MySQL(app)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        conn.execute("SELECT * FROM accounts WHERE userid = '{}' AND password ='{}'".format(userid, password, ))
        account = conn.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['userid']
            session['type'] = account['user_type']
            msg = 'Logged in successfully !'
            return redirect(url_for('posts', msg=msg))
        else:
            msg = 'Incorrect username or password !'
            return render_template('login.html', msg=msg)
    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('type', None)
    return redirect(url_for('login'))


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    msg = ''
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        email = request.form['email']
        conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        conn.execute('SELECT * FROM accounts WHERE userid = % s', (userid,))
        account = conn.fetchone()
        if account:
            msg = 'Account already exists'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address'
        elif not userid or not password or not email:
            msg = 'Please fill all details'
        else:
            conn.execute('INSERT INTO accounts (userid, password, email) VALUES (% s, % s, % s)', (userid, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
            return render_template('login.html', msg=msg)
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg=msg)


@app.route('/posts', methods=['GET', 'POST'], defaults={'opt': None})
def posts(opt):
    msg = ''
    if session['loggedin']:
        conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        conn.execute('SELECT * FROM posts')
        posts = conn.fetchall()
        for element in posts:
            data = []
            sys_data = []
            word_tokens = element['title'].split()
            filtered_sentence = [w for w in word_tokens if not w.lower() in stop_words]
            filtered_sentence = word_tokens[0]
            for w in word_tokens:
                if w not in stop_words:
                    filtered_sentence = filtered_sentence + "," + w
                    filtered_sentence = filtered_sentence.replace(".", "")
                    filtered_sentence = filtered_sentence.replace(",,", ",")
            url = "https://us-central1-fair-gist-370123.cloudfunctions.net/get-sn-suggestions"
            payload = json.dumps({
                "keywords": filtered_sentence
            })
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            res = response.json()
            print(res)
            if(len(res["result"])>0):
                sys_reply=[]
                sys_reply.append(res["result"][0]["content"])
                print(sys_reply)
                sys_reply.append("System")
                sys_reply.append(res["result"][0]["last_updated_on"])
                sys_data.append(sys_reply)
            element["sys_data"] = sys_data
            id_post = element['id']
            query_string = "SELECT a.postreply, a.post_id, a.timestamp, b.userid  FROM replies a INNER JOIN accounts b on b.id = a.account_id " \
                           "where post_id="+str(id_post)+" ORDER BY a.timestamp"
            conn.execute(query_string)
            replies = conn.fetchall()
            for tup in replies:
                reply = []
                reply.append(tup['postreply'])
                reply.append(tup['userid'])
                time = tup['timestamp']
                reply.append(time)
                data.append(reply)
            element["data"] = data
        print(posts)
        return render_template('posts.html', posts=posts)
    else:
        msg = 'Error loading Discussion Board, please try again'
        return render_template('login.html', msg=msg)


@app.route('/createpost', methods=['GET', 'POST'])
def createpost():
    msg = ''
    if request.method == 'POST':
        title = request.form['title']
        query = request.form['query']
        description = request.form['description']
        conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        conn.execute('INSERT INTO posts (title, query, description) VALUES (% s, % s, % s)',
                     (title, query, description))
        mysql.connection.commit()
        msg = 'Post created successfully!'
        url = url_for('posts', msg=msg)
        return redirect(url)
    return render_template('createpost.html', msg=msg)


@app.route('/createreply', methods=['GET', 'POST'])
def createreply():
    msg = ''
    if request.method == 'POST':
        account_id = session['id']
        postid = request.form['postid']
        reply = request.form['reply']
        conn = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        conn.execute('INSERT INTO replies(postreply, post_id, account_id) VALUES (% s, % s, % s)', (reply, postid, account_id))
        mysql.connection.commit()
        msg = 'Post Created Successfully!'
        url = url_for('posts', msg=msg)
        return redirect(url)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)
