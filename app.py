from flask import Flask, render_template, redirect, url_for, flash, request, session
from functools import wraps
import psycopg2
import os
import urlparse
import read_env
import string
import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

### <Configuring the app
app.secret_key = 'lj)0di6i8jop#7$hk&)a9%92@0n6kf96jjm4m2p^j6h^(o(%+7'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 #may want to change this?

# reading in the database address
read_env.read_env()
db_url = os.environ['DATABASE_URL']

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db = SQLAlchemy(app)
db.reflect(app=app) #this line reads in the already existing tables from the database

# Note that because models.py imports the variable db we can only import
# db subclasses after we've assigned db

from models import *

###/>

# we define this function here so we don't have to keep specifying the database address
def database_connection(db_url):
	return psycopg2.connect(
		database = db_url.path[1:],
		user = db_url.username,
		password = db_url.password,
		host = db_url.hostname,
		port = db_url.port)



# login required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap

# every time a request is made, the user's session life is restored to 12 hours
# if the user is inactive for 12 hours or more, they are logged out
@app.before_request
def make_session_permanent():
	try:
		if 'logged_in' in session:
			session.permanent = True
			app.permanent_session_lifetime = datetime.timedelta(hours=12)
	except KeyError:
		pass

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
	user = session['user']
	return render_template('dashboard.html', user=user) 


	
@app.route('/login', methods = ['GET', 'POST'])
def login():
	if request.method == 'POST':
		#conn = database_connection(db_url = db_url)
		#curs = conn.cursor()
		#curs.execute('SELECT email, password FROM users;')
		#credentials = curs.fetchall() #list of all the email-password combos in the database
		#conn.close()
		credentials = User.query.with_entities(User.email, User.password).order_by(User.id).all()
		if (request.form['email_input'], request.form['password_input']) not in credentials:
			flash('Sorry, we couldn\'t find that email-password combo.')
			return redirect(url_for('login'))
		elif 'user' in session.keys():
			flash('You\'re already logged in! You have to log out first.')
			return redirect(url_for('dashboard'))
		else:
			session['logged_in'] = True
			username = User.query.filter(User.email == request.form['email_input']).with_entities(User.username).one()[0]
			session['user'] = username[0]
			flash('Login Successful')
			return redirect('/')
	return render_template('login.html')


### - 
@app.route('/signup', methods=['GET', 'POST'])
def create_account():
	if request.method == 'POST':
		if 'username_input' in request.form.keys(): # if signup credentials were posted
			username, password, email = request.form['username_input'], request.form['password_input'], request.form['email_input']

			### if the username or email submitted is already taken...
			existing_users = User.query.order_by(User.id).all()
			existing_usernames = [user.username for user in existing_users]
			existing_emails = [user.email for user in existing_users]
			if username in existing_usernames:
				flash('Sorry, the username %s is already taken'.format(username))
				return redirect(url_for('create_account'))
			if email in existing_emails:
				flash('There is already an account registered to the email address %s'.format(email))
				return redirect(url_for('create_account'))

			# only allow characters/numbers and '_' in the username and password and only allow usernames/passwords of length <= 20
			allowed_characters = list(string.ascii_letters) + list(string.digits) + ['_']
			disallowed_characters_in_username = (not set(list(username)).issubset(allowed_characters))
			disallowed_characters_in_password = (not set(list(password)).issubset(allowed_characters))
			username_length_incorrect = (len(username) < 6) or (len(username) > 20)
			password_length_incorrect= (len(password) < 6) or (len(password) > 20)
			forbidden_creds = disallowed_characters_in_username or disallowed_characters_in_password or username_length_incorrect or password_length_incorrect

			if forbidden_creds:
				flash("""Usernames and passwords must be at least 6 character long,
				 less than 20 characters long, and can contain only letters, digits and '_' """)
				return redirect(url_for('create_account'))

			# if a field was left blank, flash error messages and redirect to same page
			if username == '':
				flash('You left the username field blank! Please enter a username.')
				return redirect(url_for('create_account'))
			if password == '':
				flash('You left the password field blank! Please enter a password.')
				return redirect(url_for('create_account'))
			if email == '':
				flash('You left the email field blank! Please enter an email address.')
				return redirect(url_for('create_account'))
			#else, proceed to make the account
			new_user_id = existing_users[-1].id + 1
			new_user = User(id=new_user_id, username=username, password=password, email=email) #note that these argument values are specified at the beginning of the create_account route
			db.session.add(new_user)
			db.session.commit()
			## need to fix this so that immediately after account creation you are logged in
			## and redirected to the dashboard
			return redirect(url_for('login')) #for the time being, just go to the login page
	return render_template('index.html')

@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	session.pop('user', None)
	flash('You were just logged out')
	return redirect(url_for('dashboard'))

@app.route('/table_test')
def table_test():
	return render_template('tableview.html')



#start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)
