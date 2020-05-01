# StockSim

## About

This web "game" built with Flask starts the user off $50,000, and allows the user to buy and sell real stocks at real prices, allowing you experience stock trading without the financial risk.

Date collected from Yahoo Finance through the yFinance module.

**WARNING:** Any changes made to data structure attributes will render any current user data unusable. There is no migration system so all JSON data will need to be updated to the current system by hand in order to become usable.

## Todo

1. *Implement history and activity. (v1.1) --- DONE*
2. *General bug fixes, improvements, and beautification of web pages. (v1.1) --- DONE*
3. *Time series chart (v1.v1) --- DONE*
4. *Enable logout button (same result can be achieved by closing browser but just for convenience) (v1.2) --- DONE*
5. *Add stop/limit options to buying/selling (v1.2) --- DONE*
6. *Orders item in nav bar for current open orders (v1.2) --- DONE*
7. *Global leaderboard (v1.3) --- DONE*
8. *Enable all dropdown menu options (v1.4) --- DONE*

## Installation

### Requirements

#### Python 3.7+

Go to [this](https://www.python.org/downloads/) link and download the python (version 3.7+) installer for your operating system.

#### Pip modules
1. flask
2. yfinance
3. mysql.connector

...all other imports should be already builtin with python or are dependencies of the modules above.

To install a pip module:
```
pip install MODULE_NAME
```
or
```
pip3 install MODULE_NAME
```
depending on what versions of python you already have on your operating system

#### MySQL

Choose the latest stable version, the community edition is fine.
Then install the version for your operating system and follow the mySQL installion insturctions

## Setup

### MySQL

In either your terminal or workbench, enter the following commands:

```sql

# Replace "databaseName" with your own database name.

CREATE database databaseName;

USE databaseName;

CREATE TABLE users (
  id int NOT NULL AUTO_INCREMENT,
  username varchar(32) NOT NULL,
  password varchar(73) NOT NULL,
  portfolio json NOT NULL,
  PRIMARY KEY (id,username),
  UNIQUE KEY id_UNIQUE (id),
  UNIQUE KEY username_UNIQUE (username)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
```

### Settings.py

First, create a settings.py file in the uppermost directory of the project. In the file, enter:

```py
PASSWORD = 'your mysql password here'
DATABASE = 'your database name'
STARTING_VALUE = 50_0000 # This is the amount of cash users have when they start the game
```

## Execution

```
cd path/to/project
```

then

```
py app.py
python app.py
python3 app.py
```
Your python command will depend on your operating system and what versions of python you already have on your computer

Enter this [link](https://localhost:5000) to get to the website on localhost (your port should default to 5000, but may change on what you have already running so check your terminal). There are many tutorials online on how to deploy the project to a real domain with Flask.

## License

MIT License - [LICENSE](LICENSE)

## Contributors / Credits

OC => [rahulmohan126](https://github.com/rahulmohan126)
