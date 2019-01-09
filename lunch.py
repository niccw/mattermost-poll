import sqlite3
from flask import jsonify

class Lunch(object):
    def __init__(self):
        self.db = "Lunch.db"

    def init_lunch_database(self):
        con = sqlite3.connect(self.db)
        cur = con.cursor()
        cur.execute("""PRAGMA user_version = 1""")
        cur.execute("""CREATE TABLE IF NOT EXISTS Lunch (
                    author_id text PRIMARY KEY,
                    restaurant text NOT NULL)""")
        con.commit()

    def add_restaurant(self,author_id,restaurant):
        con = sqlite3.connect(self.db)
        self.init_lunch_database()
        cur = con.cursor()
        try:
            cur.execute("""INSERT INTO Lunch (author_id, restaurant) VALUES (?,?)""", (author_id, restaurant))
            return True
        except sqlite3.Error as e:
            raise InvalidLunchError
            print(e)
            return False

    def rm_restaurant(self,restaurant):
        con = sqlite3.connect(self.db)
        self.init_lunch_database()
        cur = con.cursor()
        try:
            cur.execute("""DELETE FROM Lunch WHERE restaurant=?""",(restaurant))
            return True
        except sqlite3.Error as e:
            raise InvalidLunchError
            print(e)
            return False

 
    def read_restaurant(self):
        con = sqlite3.connect(self.db)
        self.init_lunch_database()
        cur = con.cursor()
        try:
            cur.execute("""SELECT restaurant FROM Lunch""")
            return [v[0] for v in cur.fetchall()]
        except sqlite3.Error as e:
            raise InvalidLunchError
            print(e)
            return False

class InvalidLunchError(Exception):
    """Raised when Lunch creation or loading failed."""
    pass