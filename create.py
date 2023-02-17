import sqlite3
conn=sqlite3.connect("project.db")
cur=conn.cursor()
# query="""CREATE TABLE users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     username TEXT NOT NULL UNIQUE,
#     password TEXT

# )"""
# cur.execute(query)

# query="""CREATE TABLE followings (
#     follower TEXT,
#     followee TEXT,
#     FOREIGN KEY (follower) references users (username),
#     FOREIGN KEY (follower) references users (username)
# )"""
# cur.execute(query)

query="""CREATE TABLE currentuser (
    currentuser TEXT,
    FOREIGN KEY (currentuser) references users (username)
)"""
cur.execute(query)
