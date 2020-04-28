from structures import *
from threading import Event as ThreadEvent
from os import urandom
import flask, math, json

database = Database()
cache = Cache()
app = flask.Flask(__name__)

app.secret_key = urandom(32).hex()

stopEvent = ThreadEvent()

print(f'Secrety Key: {app.secret_key}')


def updateAllPortfolios():
	allUsers = database.getAllUsers()

	for data in allUsers:
		user = User(json.loads(data[3]))
		user.data.update(cache)

		database.saveUser(user.id, user.getData())


def isLoggedIn() -> bool:
	if 'loggedIn' not in flask.session:
		flask.session['loggedIn'] = False

	return flask.session['loggedIn']


def addUserToSession(userRow) -> None:
	userRow = list(userRow)

	userRow[3] = json.loads(userRow[3])

	if 'blank' in userRow[3]:
		TEMPLATE = {
			"id": userRow[0],
			"username": userRow[1],
			"password": userRow[2],
			"data": {
				"portfolio": {
					"value": 50000,
					"cash": 50000,
					"cost": 0,
					"orders": [],
					"stocks": {},
					"orderCounter": 0
				},
				"history": {
					"portfolioValue": [],
					"activity": []
				}
			}
		}

		userRow[3] = TEMPLATE

		database.saveUser(userRow[0], userRow[3])

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


def cancelOrder(orderID: int) -> None:
	user = User(flask.session['user'])

	for i in range(len(user.data.portfolio.orders)):
		if user.data.portfolio.orders[i].id == orderID:
			user.data.portfolio.orders.pop(i)
			break

	database.saveUser(user.id, user.getData())
	flask.session['user'] = user.getData()


@app.errorhandler(404)
def error404(e):
	user = None
	if 'user' in flask.session:
		user = User(flask.session['user'])
	else:
		user = User()

	return flask.render_template('404.html', user=user, format=Format)


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
		user, res = database.login(flask.request.form['username'], flask.request.form['password'])

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
		portfolioData = user.data.portfolio.getDataWithCalculations(cache)

		return flask.render_template('dashboard.html', user=user, portfolio=portfolioData, format=Format)
	elif 'cancelOrder' in flask.request.form:
		cancelOrder(int(flask.request.form['cancelOrder']))

		return flask.redirect(flask.url_for('dashboard'))
	else:
		return flask.redirect(flask.url_for('stock', ticker=flask.request.form['searchTicker']))


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
		chartData = data.getChartData('y')
		user = User(flask.session['user'])
		limits = user.data.portfolio.getLimits(flask.request.args['ticker'],
											   data.info['regularMarketPrice'])

		return flask.render_template('stock.html', user=user, ticker=data.info['symbol'], data=data.info, chartData=chartData, limits=limits, format=Format)
	elif 'searchTicker' in flask.request.form:
		return flask.redirect(
			flask.url_for('stock', ticker=flask.request.form['searchTicker']))
	elif 'cancelOrder' in flask.request.form:
		cancelOrder(int(flask.request.form['cancelOrder']))

		return flask.redirect(
			flask.url_for('stock', ticker=flask.request.args['ticker']))
	else:
		# The buy/sell could not be executed because of insufficient funds or becuase none of that stock is owned (respectively)
		if int(flask.request.form['amount']) == 0:
			return flask.redirect(
				flask.url_for('stock', ticker=flask.request.args['ticker']))

		ticker = flask.request.args['ticker'].upper()
		action = flask.request.form['action']
		price = cache.get(ticker).info['regularMarketPrice']
		stopAndLimit = (int(flask.request.form['limit']),
						int(flask.request.form['stop']))
		amount = int(flask.request.form['amount'])
		user = User(flask.session['user'])

		limits = user.data.portfolio.getLimits(ticker, price)[-2:]

		user.data.history.addLotEvent(action, ticker, amount, price)

		if stopAndLimit[0] == limits[0] and stopAndLimit[1] == limits[1]:
			if action == 'BUY':
				user.data.portfolio.buy(ticker, amount, price)
			else:
				user.data.portfolio.sell(ticker, amount, price)
		else:
			orderType = 'BOTH'

			if stopAndLimit[0] == limits[0]:
				orderType = 'STOP'
			elif stopAndLimit[1] == limits[1]:
				orderType = 'LIMIT'

			user.data.portfolio.addOrder(action, ticker, amount, price,
										 orderType, stopAndLimit)

		flask.session['user'] = user.getData()
		database.saveUser(user.id, flask.session['user'])

		return flask.redirect(
			flask.url_for('stock', ticker=flask.request.args['ticker']))


@app.route('/leaderboard', methods=['GET', 'POST'])
def leaderboard():
	if not isLoggedIn():
		return flask.redirect(flask.url_for('register'))

	if flask.request.method == 'GET':
		user = User(flask.session['user'])
		portfolioData = user.data.portfolio.getDataWithCalculations(cache)

		numOfUsers = 10

		return flask.render_template('leaderboard.html', user=user, leaderboard=database.getLeaderboard(numOfUsers), format=Format)
	elif 'cancelOrder' in flask.request.form:
		cancelOrder(int(flask.request.form['cancelOrder']))

		return flask.redirect(flask.url_for('dashboard'))
	else:
		return flask.redirect(flask.url_for('stock', ticker=flask.request.form['searchTicker']))


@app.route('/logout', methods=['GET'])
def logout():
	if 'user' in flask.session:
		del flask.session['user']
		flask.session['loggedIn'] = False
	return flask.redirect(flask.url_for('register'))


if __name__ == "__main__":
	background = BackgroundProcesses(stopEvent, updateAllPortfolios)
	background.start()

	# To end the background process, uncomment the following line:
	# stopEvent.set()

	app.run(debug=True)
