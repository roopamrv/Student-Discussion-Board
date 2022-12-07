from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os

app = Flask(__name__)
app.secret_key = 'your secret key'

if os.environ.get('GAE_ENV') == 'standard':
    app.config['MYSQL_UNIX_SOCKET'] = '/cloudsql/{}'.format(os.environ.get('CLOUD_SQL_CONNECTION_NAME'))

else:
    app.config['MYSQL_HOST'] = 'localhost'
    
app.config['MYSQL_USER'] = os.environ.get('CLOUD_SQL_USERNAME')
app.config['MYSQL_PASSWORD'] = os.environ.get('CLOUD_SQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('CLOUD_SQL_DATABASE_NAME')


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
            msg = 'Incorrect username / password !'
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
        usertype = request.form['usertype']
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
            conn.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s, % s)', (userid, password, email, usertype,))
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
        msg = 'Post created successfully!'
        url = url_for('posts', msg=msg)
        return redirect(url)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)
