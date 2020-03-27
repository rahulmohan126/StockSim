from structures import *
from os import urandom
import flask, math, time, json

database = Database()
cache = Cache()
app = flask.Flask(__name__)

app.secret_key = urandom(12).hex()

print('Secrety Key: {}'.format(app.secret_key))


def isLoggedIn() -> bool:
	if 'loggedIn' not in flask.session:
		flask.session['loggedIn'] = False

	return flask.session['loggedIn']


def addUserToSession(userRow) -> None:
	userRow = list(userRow)

	userRow[3] = json.loads(userRow[3])

	if 'blank' in userRow[3]:
		TEMPLATE = {
			"id":userRow[0],
			"username":userRow[1],
			"password":userRow[2],
			"data":{
				"portfolio":{
					"value":50000,
					"cash":50000,
					"cost":0,
					"orders":[],
					"stocks":{}
				},
				"history":{
					"portfolioValue":[],
					"activity":[]
				}
			}
		}

		userRow[3] = TEMPLATE

	flask.session['user'] = userRow[3]
	flask.session['loggedIn'] = True


def validTicker(ticker: str) -> bool:
	ticker = ticker.upper().strip()
	isReal = False

	results = json.loads(
		requests.get(
			'http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en'
			.format(ticker)).text)['ResultSet']['Result']
	tickers = [result['symbol'] for result in results]

	for item in tickers:
		if ticker == item:
			isReal = True
			break

	if not isReal:
		return False
	else:
		return True


@app.errorhandler(404)
def error404(e):
	return flask.render_template('404.html', user={
		'username':'?'
	})

@app.route('/register', methods=['GET', 'POST'])
def register():
	if flask.request.method == 'GET':
		if isLoggedIn():
			return flask.redirect(flask.url_for('dashboard'))
		else:
			return flask.render_template('register.html')
	else:
		if flask.request.form['password'] != flask.request.form[
				'repeatPassword']:
			return flask.redirect(flask.url_for('register',
												invalidRepeat=True))

		user, res = database.createUser(flask.request.form['username'],
										flask.request.form['password'])

		if res is False:
			return flask.redirect(
				flask.url_for('register', invalidUsername=True))
		else:
			addUserToSession(user)
			return flask.redirect(flask.url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		if isLoggedIn():
			return flask.redirect(flask.url_for('dashboard'))
		else:
			return flask.render_template('login.html')
	else:
		user, res = database.login(flask.request.form['username'],
								   flask.request.form['password'])

		if res['username'] is False:
			return flask.redirect(flask.url_for('login', invalidUsername=True))
		elif res['password'] is False:
			return flask.redirect(flask.url_for('login', invalidPassword=True))
		else:
			addUserToSession(user)
			return flask.redirect(flask.url_for('dashboard'))


@app.route('/', methods=['GET', 'POST'])
def dashboard():
	if not isLoggedIn():
		return flask.redirect(flask.url_for('register'))

	if flask.request.method == 'GET':
		user = User(flask.session['user'])
		portfolioData, saveNeeded = user.data.portfolio.getDataWithCalculations(cache)

		if saveNeeded:
			flask.session['user'] = user.getData()
			database.saveUser(user.id, flask.session['user'])

		return flask.render_template('dashboard.html',
									 user=user,
									 portfolio=portfolioData,
									 format=Format,
									 len=len)
	else:
		return flask.redirect(
			flask.url_for('stock', ticker=flask.request.form['searchTicker']))


@app.route('/stock', methods=['GET', 'POST'])
def stock():
	if not isLoggedIn():
		return flask.redirect(flask.url_for('register'))

	if flask.request.method == 'GET':
		if 'ticker' not in flask.request.args or not validTicker(
				flask.request.args['ticker']):
			flask.abort(404)

		data = cache.get(flask.request.args['ticker'])
		data.refresh()
		chart = yearData(flask.request.args['ticker'])
		user = User(flask.session['user'])
		limits = user.data.portfolio.getLimits(flask.request.args['ticker'], data.info['regularMarketPrice'])

		return flask.render_template('stock.html',
									 user=user,
									 ticker=data.info['symbol'],
									 data=data.info,
									 testData=chart,
									 limits=limits,
									 format=Format)
	elif 'searchTicker' in flask.request.form:
		return flask.redirect(
			flask.url_for('stock', ticker=flask.request.form['searchTicker']))
	else:
		if int(flask.request.form['amount']) == 0:
			return flask.redirect(flask.url_for('stock', ticker=flask.request.args['ticker']))

		# Pass price, ticker, and type from GET to POST (through readonly invisible forms or session?)
		price = cache.get(flask.request.args['ticker'].upper()).info['regularMarketPrice']
		ticker = flask.request.args['ticker'].upper()
		action = flask.request.form['action']
		user = User(flask.session['user'])

		if action == 'BUY':
			user.data.portfolio.buy(ticker, int(flask.request.form['amount']), price)
		else:
			user.data.portfolio.sell(ticker, int(flask.request.form['amount']), price)

		flask.session['user'] = user.getData()
		database.saveUser(user.id, flask.session['user'])

		return flask.redirect(flask.url_for('stock', ticker=flask.request.args['ticker']))

app.run(debug=True)
