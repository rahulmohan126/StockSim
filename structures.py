from werkzeug.security import check_password_hash, generate_password_hash
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

	def getData(self) -> str:
		data = {
			'portfolioValue': self.portfolioValue,  # Add time to value history
			'activity': [x.getData() for x in self.activity]
		}

		return data

	def setData(self, data: dict) -> None:
		self.portfolioValue = data['portfolioValue']
		self.activity = [
			ActivityEvent(data['activity'][i])
			for i in range(len(data['activity']))
		]


class Portfolio:
	def __init__(self, data: dict = None):
		self.value = 50_000
		self.cash = 50_000 # Intial cash balance and therefore value
		self.cost = 0
		self.orders = []
		self.stocks = {}

		if data is not None:
			self.setData(data)

	def buy(self, ticker: str, amount: int, price : float) -> None:
		self.cash -= amount * price
		self.cost += amount * price
		
		if ticker not in self.stocks:
			self.stocks[ticker] = Stock({
				'ticker': ticker,
				'totalStake': 0,
				'costBasis': amount * price,
				'lots': []
			})
		
		self.stocks[ticker].addLot(Lot({
			'shares': amount,
			'price': price,
			'time': time.time()
		}))

	def sell(self, ticker: str, amount: int, price : float) -> None:
		self.cash += amount * price
		self.cost -= amount * price
		
		self.stocks[ticker].addLot(Lot({
			'shares': -amount,
			'price': price,
			'time': time.time()
		}))
	
	def calculateValue(self, cache) -> bool:
		newValue = 0
		for ticker in self.stocks.keys():
			newValue += self.stocks[ticker].getValue(cache.get(ticker).info)
		
		if self.value != newValue:
			return False
		else:
			self.value = newValue
			return True

	def getLimits(self, ticker: str, price: float) -> tuple:
			ticker = ticker.upper()
			
			limits = [0, 0, 0, 0]
			
			# BUY
			limits[1] = math.floor(self.cash / price)
			
			# SELL
			if ticker not in self.stocks:
				pass
			else:
				limits[2] = 1
				limits[3] = self.stocks[ticker].totalStake
			
			return(limits)

	def getData(self) -> str:
		stocksData = {}
		for ticker in self.stocks.keys():
			stocksData[ticker] = self.stocks[ticker].getData()

		data = {
			'value': self.value,
			'cash': self.cash,
			'cost': self.cost,
			'orders': [x.getData() for x in self.orders],
			'stocks': stocksData
		}

		return data

	def getDataWithCalculations(self, cache) -> dict:
		stocksData = [self.stocks[ticker].getDataWithCalculations(cache) for ticker in self.stocks.keys()]
		dayGain = sum([stock['dayGain'] for stock in stocksData])

		newValueExists = self.calculateValue(cache)
		
		data = {
			'value': self.value,
			'cash': self.cash,
			'cost': self.cost,
			'orders': [x.getData() for x in self.orders],
			'stocks': stocksData,
			'netGain': self.value - 50000,
			'netGainPercentage': (self.value - 50000) / 50000 * 100,
			'dayGain': dayGain,
			'dayGainPercentage': dayGain / self.value * 100
		}

		return (data, newValueExists)

	def setData(self, data: dict) -> None:
		self.value = data['value']
		self.cash = data['cash']
		self.cost = data['cost']
		self.orders = [
			Order(data['orders'][i]) for i in range(len(data['orders']))
		]

		for key in data['stocks'].keys():
			self.stocks[key] = Stock(data['stocks'][key])


class ActivityEvent:
	def __init__(self, data: dict = None):
		self.time = 0
		self.description = ''

		if data is not None:
			self.setData(data)

	def getData(self) -> str:
		data = {'time': self.time, 'description': self.description}

		return data

	def setData(self, data: dict) -> None:
		self.time = data['time']
		self.description = data['description']


class Order:
	def __init__(self, data: dict = None):
		self.time = 0
		self.action = ''  # BUY or SELL
		self.type = ''  # STOP, LIMIT, BOTH
		self.limits = [0, 0]
		self.ticker = ''

		if data is not None:
			self.setData(data)

	def getData(self) -> str:
		data = {
			'time': self.time,
			'action': self.action,
			'type': self.type,
			'limits': self.limits,
			'ticker': self.ticker
		}

		return data

	def setData(self, data: dict) -> None:
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
			'ticker': self.ticker,
			'totalStake': self.totalStake,
			'costBasis': self.costBasis,
			'lots': lots,
			'dayGain': sum([lot['dayGain'] for lot in lots]),
			'dayGainPercentage': (sum([lot['dayGain'] for lot in lots]) / (info['previousClose'] * self.totalStake) * 100) if self.totalStake is not 0 else 0,
			'netGain': sum([lot['netGain'] for lot in lots]),
			'netGainPercentage': sum([lot['netGain'] for lot in lots]) / self.costBasis * 100,
			'price': info['regularMarketPrice'],
			'change': info['regularMarketPrice'] - info['previousClose'],
			'changePercentage': (info['regularMarketPrice'] - info['previousClose']) / info['previousClose'] * 100,
			'open': info['regularMarketOpen'],
			'close': info['previousClose'],
			'volume': info['regularMarketVolume'],
			'marketCap': info['marketCap']
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
			'shares': self.shares,
			'price': self.price,
			'time': self.time,
			'netGain': (info['regularMarketPrice'] - self.price) * self.shares,
			'dayGain': (info['regularMarketPrice'] - info['previousClose']) * self.shares
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
			return self.stocks[ticker]
		else:
			self.add(ticker)
			return self.stocks[ticker]

	def add(self, ticker):
		self.stocks[ticker] = StockData(yfinance.Ticker(ticker))

	def refresh(self):
		for ticker, data in self.stocks.items():
			data.refresh()


class StockData:
	def __init__(self, ticker):
		self.ticker = ticker
		self.info = self.ticker.info
		self.lastUpdated = time.time()

	def refresh(self):
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


def yearData(ticker: str) -> list:
	rawData = yfinance.Ticker(ticker).history(period='1y', interval='1mo')

	parsedData = [
		float(rawData['Close'][i]) for i in rawData.index
		if not math.isnan(rawData['Close'][i])
	]

	return parsedData


class Database:
	def __init__(self):
		self.db = mysql.connector.connect(
			user='root',
			password=PASSWORD,
			host='localhost',
			database=DATABASE,
			auth_plugin='mysql_native_password'
		)

		self.cursor = self.db.cursor()

	def getUser(self, username : str) -> dict:
		iterator = self.cursor.execute('USE stock_simulator; SELECT DISTINCT * FROM users where username = %(username)s;', {
			'username': username
		}, multi=True)

		try:
			for result in iterator:
				if result.with_rows:
					return result.fetchall()[0]
		except:
			return None

	def login(self, username : str, password : str) -> tuple:
		user = self.getUser(username)
		if user is None:
			return (None, {
				'username': False,
				'password': False
			})

		if check_password_hash('sha256$' + user[2], password):
			return (user, {
				'username': True,
				'password': True
			})
		else:
			return (None, {
				'username': True,
				'password': False
			})

	def createUser(self, username : str, password : str) -> tuple:
		if self.checkIfUserExists(username):
			return (None, False)

		print(username, password)
		
		hashedPassword = generate_password_hash(password, 'sha256')[7:]
		
		self.cursor.execute('INSERT INTO users (username, password, portfolio) VALUES(%(username)s, %(password)s, %(portfolio)s);', {
			'username': username,
			'password': hashedPassword,
			'portfolio': '{"blank":"object"}'
		})

		self.db.commit()

		return (self.getUser(username), True)
	
	def checkIfUserExists(self, username : str) -> bool:
		iterator = self.cursor.execute('SELECT * FROM users WHERE username = %(username)s LIMIT 1;', {
			'username': username
		}, multi=True)

		try:
			for result in iterator:
				if result.with_rows and result.fetchall()[0] != None:
					return True
		except:
			return False

	def saveUser(self, userID : int, newUserData : dict) -> None:
		self.cursor.execute('UPDATE users SET portfolio = %(newData)s WHERE (id = %(id)s);', {
			'newData': json.dumps(newUserData),
			'id': str(userID)
		})

		self.db.commit()