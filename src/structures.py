from werkzeug.security import check_password_hash, generate_password_hash
from threading import Thread
from settings import *
import json, time, ssl, yfinance, requests, math, mysql.connector

ssl._create_default_https_context = ssl._create_unverified_context


class User:
	def __init__(self, data: dict = None):
		self.id = 0
		self.username = ''
		self.password = ''  # Hashed
		self.data = UserData()

		if data is not None:
			self.setData(data)

	def getData(self) -> str:
		data = {
			'id': self.id,
			'username': self.username,
			'password': self.password,
			'data': self.data.getData()
		}

		return data

	def setData(self, data: dict) -> None:
		self.id = data['id']
		self.username = data['username']
		self.password = data['password']
		self.data.setData(data['data'])


class UserData:
	def __init__(self, data: dict = None):
		self.portfolio = Portfolio()
		self.history = History()

		if data is not None:
			self.setData(data)

	def update(self, cache):
		# Updates the portfolio values with the most recent.
		self.portfolio.getDataWithCalculations(cache)
		self.history.addPortfolioValue(time.time(), self.portfolio.value)

		# Executes the currenct open orders if ready
		for order in self.portfolio.orders:
			info = cache.get(order.ticker).info
			price = info['regularMarketPrice']

			if order.isReady(info):
				# Ensures that their is enough money to execute the buy order
				if order.action == 'BUY' and self.portfolio.cash >= order.amount * price:
					self.portfolio.buy(order.ticker, order.amount, price)
				# Ensures that their is enough shares for the sell order
				elif order.action == 'SELL' and self.portfolio.stocks[
						order.ticker].totalStake >= order.amount:
					self.portfolio.price(order.ticker, order.amount, price)

	def getData(self) -> str:
		data = {
			'portfolio': self.portfolio.getData(),
			'history': self.history.getData()
		}

		return data

	def setData(self, data: dict) -> None:
		self.portfolio.setData(data['portfolio'])
		self.history.setData(data['history'])


class History:
	def __init__(self, data: dict = None):
		self.portfolioValue = []
		self.activity = []

		if data is not None:
			self.setData(data)

	def addPortfolioValue(self, currentTime, currentValue):
		self.portfolioValue.append(
			ActivityEvent({
				'time': currentTime,
				'value': currentValue
			}))

	def addLotEvent(self, lotType, ticker, amount, price):
		self.activity.append(
			ActivityEvent({
				'time':
				time.time(),
				'value':
				f'{lotType}: {amount} shares of {ticker} at ${price}'
			}))

	def getData(self) -> str:
		data = {
			'portfolioValue':
			[x.getData()
			 for x in self.portfolioValue],  # Add time to value history
			'activity': [x.getData() for x in self.activity]
		}

		return data

	def setData(self, data: dict) -> None:
		self.portfolioValue = [
			ActivityEvent(data['portfolioValue'][i])
			for i in range(len(data['portfolioValue']))
		]

		self.activity = [
			ActivityEvent(data['activity'][i])
			for i in range(len(data['activity']))
		]


class Portfolio:
	def __init__(self, data: dict = None):
		self.cash = STARTING_VALUE  # Intial cash balance and therefore value
		self.value = self.cash
		self.cost = 0
		self.orders = []
		self.stocks = {}
		self.orderCounter = 0

		if data is not None:
			self.setData(data)

	def calculateValue(self, stocksData: dict) -> None:
		newValue = self.cash
		for stock in stocksData:
			newValue += stock['price'] * stock['totalStake']

		self.value = newValue

	def addOrder(self, action: str, ticker: str, amount: int, price: float,
				 orderType: str, limits: str):
		self.orders.append(
			Order({
				'id': self.orderCounter,
				'time': time.time(),
				'action': action,
				'type': orderType,
				'limits': limits,
				'ticker': ticker
			}))

		self.orderCounter += 1

	def buy(self, ticker: str, amount: int, price: float) -> None:
		self.cash -= amount * price
		self.cost += amount * price

		if ticker not in self.stocks:
			self.stocks[ticker] = Stock({
				'ticker': ticker,
				'totalStake': 0,
				'costBasis': amount * price,
				'lots': []
			})

		self.stocks[ticker].addLot(
			Lot({
				'shares': amount,
				'price': price,
				'time': time.time()
			}))

	def sell(self, ticker: str, amount: int, price: float) -> None:
		self.cash += amount * price
		self.cost -= amount * price

		self.stocks[ticker].addLot(
			Lot({
				'shares': -amount,
				'price': price,
				'time': time.time()
			}))

	def getLimits(self, ticker: str, price: float) -> tuple:
		ticker = ticker.upper()

		limits = [0] * 6

		# BUY
		limits[1] = math.floor(self.cash / price)

		# SELL
		if ticker not in self.stocks:
			pass
		else:
			limits[2] = 1
			limits[3] = self.stocks[ticker].totalStake

		limits[4] = round(0.5 * price)
		limits[5] = round(1.5 * price)

		return (limits)

	def getData(self) -> str:
		stocksData = {}
		for ticker in self.stocks.keys():
			stocksData[ticker] = self.stocks[ticker].getData()

		data = {
			'value': self.value,
			'cash': self.cash,
			'cost': self.cost,
			'orders': [x.getData() for x in self.orders],
			'stocks': stocksData,
			'orderCounter': self.orderCounter
		}

		return data

	def getDataWithCalculations(self, cache) -> dict:
		stocksData = [
			self.stocks[ticker].getDataWithCalculations(cache)
			for ticker in self.stocks.keys()
		]

		dayGain = sum([stock['dayGain'] for stock in stocksData])

		self.calculateValue(stocksData)

		data = {
			'value': self.value,
			'cash': self.cash,
			'cost': self.cost,
			'orders': [x.getData() for x in self.orders],
			'stocks': stocksData,
			'netGain': self.value - STARTING_VALUE,
			'netGainPercentage':
			(self.value - STARTING_VALUE) / STARTING_VALUE * 100,
			'dayGain': dayGain,
			'dayGainPercentage': dayGain / self.value * 100,
			'orderCounter': self.orderCounter
		}

		return data

	def setData(self, data: dict) -> None:
		self.value = data['value']
		self.cash = data['cash']
		self.cost = data['cost']
		self.orders = [
			Order(data['orders'][i]) for i in range(len(data['orders']))
		]

		for key in data['stocks'].keys():
			self.stocks[key] = Stock(data['stocks'][key])

		self.orderCounter = data['orderCounter']


class ActivityEvent:
	def __init__(self, data: dict = None):
		self.time = 0
		self.value = ''  # Default value is str but can be an int as well

		if data is not None:
			self.setData(data)

	def getData(self) -> str:
		data = {'time': self.time, 'value': self.value}

		return data

	def setData(self, data: dict) -> None:
		self.time = data['time']
		self.value = data['value']


class Order:
	def __init__(self, data: dict = None):
		self.id = 0
		self.action = ''  # BUY or SELL

		self.type = ''
		# STOP, LIMIT, BOTH. No stop/limit orders are executed immediately, so
		# order objects are not created

		self.limits = [0, 0]
		self.ticker = ''

		if data is not None:
			self.setData(data)

	def isReady(self, info) -> bool:
		# Checks if the order is ready to be executed
		stopTrue = info['regularMarketPrice'] > self.limits[1]
		limitTrue = info['regularMarketPrice'] < self.limits[0]

		if self.type == 'STOP' and stopTrue:
			return True
		elif self.type == 'LIMIT' and limitTrue:
			return True
		elif self.type == 'BOTH' and (stopTrue or limitTrue):
			return True

		return False

	def getData(self) -> str:
		data = {
			'id': self.id,
			'time': self.time,
			'action': self.action,
			'type': self.type,
			'limits': self.limits,
			'ticker': self.ticker
		}

		return data

	def setData(self, data: dict) -> None:
		self.id = data['id']
		self.time = data['time']
		self.action = data['action']
		self.type = data['type']
		self.limits = data['limits']
		self.ticker = data['ticker']


class Stock:
	def __init__(self, data: dict = None):
		self.ticker = ''
		self.totalStake = 0
		self.costBasis = 0
		self.lots = []

		if data is not None:
			self.setData(data)

	def addLot(self, newLot):
		self.totalStake += newLot.shares
		self.costBasis += newLot.price * newLot.shares
		self.lots.append(newLot)

	def getData(self) -> str:
		data = {
			'ticker': self.ticker,
			'totalStake': self.totalStake,
			'costBasis': self.costBasis,
			'lots': [x.getData() for x in self.lots]
		}
		return data

	def getDataWithCalculations(self, cache) -> dict:
		info = cache.get(self.ticker).info

		lots = [x.getDataWithCalculations(info) for x in self.lots]

		data = {
			'ticker':
			self.ticker,
			'totalStake':
			self.totalStake,
			'costBasis':
			self.costBasis,
			'lots':
			lots,
			'dayGain':
			sum([lot['dayGain'] for lot in lots]),
			'dayGainPercentage': (sum([lot['dayGain'] for lot in lots]) /
								  (info['previousClose'] * self.totalStake) *
								  100) if self.totalStake is not 0 else 0,
			'netGain':
			sum([lot['netGain'] for lot in lots]),
			'netGainPercentage':
			sum([lot['netGain'] for lot in lots]) / self.costBasis * 100,
			'price':
			info['regularMarketPrice'],
			'change':
			info['regularMarketPrice'] - info['previousClose'],
			'changePercentage':
			(info['regularMarketPrice'] - info['previousClose']) /
			info['previousClose'] * 100,
			'open':
			info['regularMarketOpen'],
			'close':
			info['previousClose'],
			'volume':
			info['regularMarketVolume'],
			'marketCap':
			info['marketCap']
		}

		return data

	def getValue(self, info):
		return self.totalStake * info['regularMarketPrice']

	def setData(self, data: dict) -> None:
		self.ticker = data['ticker']
		self.totalStake = data['totalStake']
		self.costBasis = data['costBasis']
		self.lots = [Lot(data['lots'][i]) for i in range(len(data['lots']))]


class Lot:
	def __init__(self, data: dict = None):
		self.shares = ''
		self.price = 0
		self.time = 0

		if data is not None:
			self.setData(data)

	def getData(self) -> str:
		data = {
			'shares': self.shares,
			'price': self.price,
			'time': self.time,
		}

		return data

	def getDataWithCalculations(self, info) -> dict:
		data = {
			'shares':
			self.shares,
			'price':
			self.price,
			'time':
			self.time,
			'netGain': (info['regularMarketPrice'] - self.price) * self.shares,
			'dayGain':
			(info['regularMarketPrice'] - info['previousClose']) * self.shares
		}

		return data

	def setData(self, data: dict) -> None:
		self.shares = data['shares']
		self.price = data['price']
		self.time = data['time']


class Cache:
	def __init__(self):
		self.stocks = {}

	def get(self, ticker):
		if ticker in self.stocks:
			self.stocks[ticker].refresh()
			return self.stocks[ticker]
		else:
			self.add(ticker)
			return self.stocks[ticker]

	def add(self, ticker):
		self.stocks[ticker] = StockData(yfinance.Ticker(ticker))


class StockData:
	def __init__(self, ticker):
		self.ticker = ticker
		self.info = self.ticker.info
		self.lastUpdated = time.time()

	def getChartData(self, unit: str) -> list:
		unitMap = {'y': '1d', 'm': '1h', 'w': '1h', 'd': '1s'}

		rawData = self.ticker.history(period='1' + unit,
									  interval=unitMap[unit])
		parsedData = []

		for i in range(len(rawData)):
			row = rawData.iloc[i]
			parsedData.append({
				't': row.name.value / 1_000_000,
				'y': row['Close']
			})

		return str(parsedData).replace("'", '')

	def refresh(self):
		# Only refreshes if it has been 30 seconds since last updated
		# Refreshing only occurs when data is called in order to minimize background processes.
		if time.time() > self.lastUpdated + 30:
			self.info = self.ticker.info
			self.lastUpdated = time.time()


class Format:
	@staticmethod
	def number(number: float) -> str:
		suffix = ''
		if number > 10e11:
			suffix = 'T'
			number /= 10e11
		elif number > 10e8:
			suffix = 'B'
			number /= 10e8
		elif number > 10e5:
			suffix = 'M'
			number /= 10e5

		number = round(number, 2)

		return '{:,}'.format(abs(number)) + suffix

	@staticmethod
	def sign(number: float) -> str:
		if number < 0:
			return '-'
		elif number > 0:
			return '+'
		else:
			return ''

	@staticmethod
	def color(number: float) -> str:
		if number < 0:
			return 'danger'
		elif number > 0:
			return 'success'
		else:
			return 'secondary'

	@staticmethod
	def abs(number: float) -> float:
		return abs(number)

	@staticmethod
	def time(number: float) -> str:
		return time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(number))

	@staticmethod
	def timeAlt(number: float) -> str:
		return time.strftime('%B %d, %Y', time.localtime(number))

	@staticmethod
	def reverseList(l: list):
		return reversed(l)


class Database:
	def __init__(self):
		self.db = mysql.connector.connect(user='root',
										  password=PASSWORD,
										  host='localhost',
										  database=DATABASE,
										  auth_plugin='mysql_native_password')

		self.cursor = self.db.cursor()

	def getUser(self, username: str) -> dict:
		iterator = self.cursor.execute(
			'USE stock_simulator; SELECT DISTINCT * FROM users where username = %(username)s;',
			{'username': username},
			multi=True)

		try:
			for result in iterator:
				if result.with_rows:
					return result.fetchall()[0]
		except:
			return None

	def login(self, username: str, password: str) -> tuple:
		user = self.getUser(username)
		if user is None:
			return (None, {'username': False, 'password': False})

		if check_password_hash('sha256$' + user[2], password):
			return (user, {'username': True, 'password': True})
		else:
			return (None, {'username': True, 'password': False})

	def createUser(self, username: str, password: str) -> tuple:
		if self.checkIfUserExists(username):
			return (None, False)

		print(username, password)

		hashedPassword = generate_password_hash(password, 'sha256')[7:]

		self.cursor.execute(
			'INSERT INTO users (username, password, portfolio) VALUES(%(username)s, %(password)s, %(portfolio)s);',
			{
				'username': username,
				'password': hashedPassword,
				'portfolio': '{"blank":"object"}'
			})

		self.db.commit()

		return (self.getUser(username), True)

	def checkIfUserExists(self, username: str) -> bool:
		iterator = self.cursor.execute(
			'SELECT * FROM users WHERE username = %(username)s LIMIT 1;',
			{'username': username},
			multi=True)

		try:
			for result in iterator:
				if result.with_rows and result.fetchall()[0] != None:
					return True
		except:
			return False

	def saveUser(self, userID: int, newUserData: dict) -> None:
		self.cursor.execute(
			'UPDATE users SET portfolio = %(newData)s WHERE (id = %(id)s);', {
				'newData': json.dumps(newUserData),
				'id': str(userID)
			})

		self.db.commit()

	def getAllUsers(self) -> list:
		iterator = self.cursor.execute(
			'USE stock_simulator; SELECT * FROM stock_simulator.users;',
			multi=True)

		try:
			for result in iterator:
				if result.with_rows:
					return result.fetchall()
		except:
			return None


class BackgroundProcesses(Thread):
	def __init__(self, stopTrigger, function):
		Thread.__init__(self)
		self.stopTrigger = stopTrigger
		self.function = function

	def run(self):
		# Wait value in seconds. Waits 1h between checks to not overload the
		# program.
		while not self.stopTrigger.wait(10):
			print('Started background processes')
			self.function()
		print('Finished background processes')
