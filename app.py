from flask import Flask,render_template,request,redirect,url_for, session,jsonify
from flask_caching import Cache
from flask_restful import Resource,Api
from celery_sys import make_celery
import csv
import datetime,time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from celery.schedules import crontab
from celery.utils.log import get_task_logger
# from pathlib import Path
import shutil,os
from werkzeug.utils import secure_filename
from datetime import datetime,timedelta
from functools import wraps
import jwt
import sqlite3 
from secret import secretkey

app = Flask(__name__)
logger = get_task_logger(__name__)
api=Api(app)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)

app.config['SECRET_KEY'] = secretkey
app.config['UPLOAD_FOLDER'] = '/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/'
cache = Cache(app, config={'CACHE_TYPE':'simple'})


SMTP_SERVER_HOST = 'smtp.gmail.com'
SMTP_SERVER_PORT = 587
SENDER_ADDRESS = "dummy.tanmayb@gmail.com"
SENDER_PASSWORD = "bjdzqdvfybswpkkq"

celery = make_celery(app)


def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'Alert!': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            if datetime.strptime(data['expiration'], '%Y-%m-%d %H:%M:%S.%f') < datetime.utcnow():
                return jsonify({"Token has expired"}), 403
        except:
            return jsonify({'Message': 'Invalid token'}), 403
        return func(*args, **kwargs)
    return decorated

@app.before_request
def require_login():
    allowed_routes = ['login', 'register']
    if request.endpoint not in allowed_routes and 'username' not in session:
        return redirect('/login')


@celery.task()
def send_email(to_address,subject,message):
    msg = MIMEMultipart()
    msg["From"] = SENDER_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "html"))

    s = smtplib.SMTP(host=SMTP_SERVER_HOST, port= SMTP_SERVER_PORT)
    s.starttls()
    s.login(SENDER_ADDRESS,SENDER_PASSWORD)
    s.send_message(msg)
    s.quit()

    return "Mail Sent"


@celery.on_after_configure.connect
def setup_periodic_task(sender, **kwargs):
    
    conn = sqlite3.connect("project.db")
    cur = conn.cursor()
    cur.execute("""SELECT currentuser FROM currentuser""")
    currentuser = cur.fetchone()[0]
    cur.execute("""SELECT email FROM users WHERE username = (SELECT currentuser FROM currentuser)""")
    email = cur.fetchone()[0]

    current_user_credentials= {"name" : currentuser, "email" : email}

    cur.execute("""SELECT datetime('now','localtime')""")
    today = cur.fetchone()[0][:10]
    viewedtoday=0
    query = """SELECT lastlogin FROM users WHERE username = (SELECT currentuser FROM currentuser) """
    cur.execute(query)
    date = cur.fetchone()[0]
    if date[:10] == today:
        viewedtoday=1

    if not viewedtoday:
        sender.add_periodic_task(
        crontab(hour=19,minute=0),
        send_email.s(current_user_credentials["email"], subject="BlogPro View Reminder", message="You haven't checked your feed today. Go to this link to check http://192.168.27.156:8080/"),
        name = "view reminder"
        )

    else:
        query = """SELECT timestamp FROM posts WHERE username = (SELECT currentuser FROM currentuser) """
        cur.execute(query)
        datess = cur.fetchall()
        postedtoday=0
        for dates in datess:
            for date in dates:
                if date[:10] == today:
                    postedtoday=1
        if not postedtoday:
            sender.add_periodic_task(
            crontab(hour=19,minute=0),
            send_email.s(current_user_credentials["email"], subject="BlogPro Post Reminder", message="You haven't Posted Anything today. Go to this link to post http://192.168.27.156:8080/addpost"),
            name = "post reminder"
            )

    sender.add_periodic_task(
        crontab(day=1,hour=10,minute=0),
        send_email.s(current_user_credentials["email"], subject="BlogPro Monthly Progress Report", message=getreport()),
        name = "monthly progress report"
    )

#Monthly Progress Report 
def getreport():
    
    conn = sqlite3.connect("project.db")
    cur = conn.cursor()
    cur.execute("""SELECT datetime('now','localtime')""")
    today = cur.fetchone()[0][:7]
    month=''
    #Calculate past month
    if today[5] == '0' and today[6] == '1':
        month = str(int(today[:4]) - 1) + '-' + '12' 
    elif today[5] == '1' and today[6] == '0':
        month = today[:4] + '-' + '09'
    else:
        month = today[:4] + '-' + today[5] + str(int(today[6]) - 1)

    cur.execute("""SELECT timestamp FROM posts WHERE username = (SELECT currentuser FROM currentuser) """)
    datess = cur.fetchall()
    list1=[]
    for dates in datess:
        for date in dates:
            if date[:7] == month:
                list1.append(date)
    cur.execute("""SELECT timestamp FROM followings WHERE followee = (SELECT currentuser FROM currentuser)""")
    datess = cur.fetchall()
    
    list2=[]
    for dates in datess:
        for date in dates:
            if date[:7] == month:
                list2.append(date)
    
    cur.execute("""SELECT timestamp FROM followings WHERE follower = (SELECT currentuser FROM currentuser)""")
    datess = cur.fetchall()
    
    list3=[]
    for dates in datess:
        for date in dates:
            if date[:7] == month:
                list3.append(date)
    print(len(list2), len(list3))
    conn.close()
    message= "Here is your monthly progress report <br> Number of Posts made last month:  " + str(len(list1)) + "<br> Number of Followers made last month:  " + str(len(list2)) + "<br> Number of People You Followed last month:  " + str(len(list3))
    
    return message

@app.route('/login', methods=['GET','POST'])
def login(): 
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("project.db")
        cur = conn.cursor()
        query = """SELECT * FROM users WHERE username=? AND password=?"""
        cur.execute(query, (username, password))
        rows = cur.fetchall()

        if len(rows) == 1:
            conn=sqlite3.connect("project.db")
            cur=conn.cursor()
            cur.execute("""DELETE FROM currentuser""")
            query="""INSERT INTO currentuser VALUES (?)"""
            cur.execute(query, (username,))
            cur.execute("""SELECT datetime('now','localtime')""")
            timestamp = cur.fetchone()[0]
            query="""UPDATE users SET lastlogin = ? WHERE username = ?"""
            cur.execute(query, (timestamp, username,))
            conn.commit()

            session['logged_in'] = True
            session['username'] = username

            token = jwt.encode({
                'user': request.form['username'],
                'expiration': str(datetime.utcnow() + timedelta(minutes=30))
            },app.config['SECRET_KEY'])
            
            return render_template('auth_successfull.html', token=token)
        else:
            return redirect(url_for('register'))
       
    return render_template('login.html') 

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# If login fails, you'll have to register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        if request.files['file'].filename == '' or request.form['name'] == '' or request.form['username'] == '' or request.form['password'] == '' or request.form['email'] == '':
                return render_template("register.html")

        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = sqlite3.connect("project.db")
        cur = conn.cursor()
        cur.execute("""SELECT username FROM users""")
        rows = cur.fetchall()
        for row in rows:
            if request.form['username'] == row[0]:
                return "Username already exists <a href='/register'> Try Register again</a>"

        query = """INSERT INTO users (name,email,username,password) VALUES (?,?,?,?)"""
        cur.execute(query, (name, email, username, password))
        conn.commit()

        if cur.rowcount == 1:
            conn=sqlite3.connect("project.db")
            cur=conn.cursor()
            cur.execute("""DELETE FROM currentuser""")
            query="""INSERT INTO currentuser VALUES (?)"""
            cur.execute(query, (username,))
            fname = username + '.jpg'
            f = request.files['file']
            f.save(secure_filename(fname))
            shutil.move('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/' + fname , '/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/')
            print("image uploaded successfully")
            conn=sqlite3.connect("project.db")
            cur=conn.cursor()
            cur.execute("""DELETE FROM currentuser""")
            query="""INSERT INTO currentuser VALUES (?)"""
            cur.execute(query, (username,))
            conn.commit()
            return redirect(url_for('index'))
        else:
            return "Something went wrong"
    
    return render_template('register.html')
    

# conn=sqlite3.connect("project.db")
# cur=conn.cursor()
# query="""SELECT currentuser FROM currentuser"""
# cur.execute(query)
# user = cur.fetchone()[0]
# fname = user + '.jpg'
# f = request.files['file']
# f.save(secure_filename(fname))
# shutil.move('D:\\Tanmay Bholane\\Visual Studio Code\\BLOG_LITE\\' + fname , 'D:\\Tanmay Bholane\\Visual Studio Code\\BLOG_LITE\\static')
# print("done")


@app.route("/", methods=['GET', 'POST'])
@cache.cached(timeout=20)
def index():
    
    if request.method == "POST":
        name=request.form['search'] 
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        name = '%' + name + '%'
        query="""SELECT username FROM users WHERE username LIKE ? """
        cur.execute(query,(name,))
        rows = cur.fetchall()
        accounts=[]
        for i in rows:
            accounts.append(i[0])
        cur.execute("""DELETE FROM searchresults""")
        for i in accounts:
            query="""INSERT INTO searchresults VALUES (?)"""
            cur.execute(query,(i,))  
        conn.commit()  
        return render_template("search.html")  
    return render_template("feed.html")


@app.route("/followingslist")
@cache.cached(timeout=30)
def followings():
    return render_template("followings.html")

@app.route("/profile/<username>", methods=['GET'])
@cache.cached(timeout=20)
def profile(username):
    conn=sqlite3.connect("project.db")
    cur=conn.cursor()
    cur.execute("""DELETE FROM requesteduser""")
    query="""INSERT INTO requesteduser VALUES (?)"""
    cur.execute(query,(username,))
    conn.commit()
    return render_template("profile.html")

@app.route("/addpost", methods=['GET', 'POST'])
def addpost():
    if request.method=="POST":
        caption =  request.form['caption']
        
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        cur.execute("""SELECT currentuser FROM currentuser""")
        user = cur.fetchone()[0]
        cur.execute("""SELECT datetime('now','localtime')""")
        timestamp = cur.fetchone()[0]
        query="""INSERT INTO posts (username,caption,timestamp) VALUES (?,?,?)"""
        cur.execute(query,(user,caption,timestamp))
        cur.execute("""SELECT last_insert_rowid()""")
        imgid = str(cur.fetchone()[0])
        fname = imgid + '.jpg'
        f = request.files['img']
        f.save(secure_filename(fname))
        shutil.move('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/' + fname , '/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/')
        print("done")
        conn.commit()
        return redirect(url_for('index'))
    return render_template("addpost.html")

@app.route("/unfollow/<flag>/<username>/", methods=['GET', 'POST'])
def unfollow(flag,username):
    conn=sqlite3.connect("project.db")
    cur=conn.cursor()
    query="""SELECT currentuser FROM currentuser"""
    cur.execute(query)
    current_user = cur.fetchone()[0]
    query="""DELETE FROM followings WHERE follower= ? AND followee = ?"""
    cur.execute(query, (current_user, username))
    cur.execute("""DELETE FROM requesteduser""")
    query="""INSERT INTO requesteduser VALUES (?)"""
    cur.execute(query,(username,))
    conn.commit()
    conn.close()
    if flag == '1':
        return render_template('search.html')  
    else:
        return redirect('/profile/' + username)

@app.route("/follow/<flag>/<username>/", methods=['GET', 'POST'])
def follow(flag,username):
    print(flag,username)
    conn=sqlite3.connect("project.db")
    cur=conn.cursor()
    query="""SELECT currentuser FROM currentuser"""
    cur.execute(query)
    current_user = cur.fetchone()[0]
    query="""INSERT INTO followings (follower,followee,timestamp) VALUES (?,?,(SELECT datetime('now','localtime')))"""
    cur.execute(query, (current_user, username))
    cur.execute("""DELETE FROM requesteduser""")
    query="""INSERT INTO requesteduser VALUES (?)"""
    cur.execute(query,(username,))
    conn.commit()
    conn.close()
    if flag == '1':
        return render_template('search.html') 
    else:
        return redirect('/profile/' + username)

@app.route("/editprofile", methods=['GET', 'POST'])
def editprofile():
    if request.method=="POST":
        try:
            dontreplaceimage = request.form['options']
        except:
            dontreplaceimage = "FALSE"
        try:
            dontreplacecaption = request.form['options2']
        except:
            dontreplacecaption = "FALSE"

        if request.files['img'].filename == '':
            if dontreplaceimage == "FALSE":
                return render_template("editprofile.html")

        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT currentuser FROM currentuser"""
        cur.execute(query)
        current_user = cur.fetchone()[0]
        if dontreplaceimage == "FALSE":
            fname = current_user + '.jpg'
            os.remove('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/' + current_user + '.jpg')
            f = request.files['img']
            f.save(secure_filename(fname))
            shutil.move('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/' + fname , '/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/')
        
        if dontreplacecaption == "FALSE":
            caption=request.form['caption']
            query="""UPDATE users SET bio = ? WHERE username = ?"""
            cur.execute(query,(caption,current_user))
            conn.commit()
        return redirect('/profile/' + current_user)
    return render_template("editprofile.html")

@celery.task()
def export_posts():
    conn=sqlite3.connect("project.db")
    cur=conn.cursor()
    cur.execute("""SELECT * FROM posts WHERE username = (SELECT currentuser FROM currentuser)""")
    rows = cur.fetchall()
    nested_list=[]
    for row in rows:
        l=[]
        for i in row:
            l.append(i)
        nested_list.append(l)
    with open('posts.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'username', 'caption', 'timestamp'])
        for i in nested_list:
            writer.writerow(i)

    cur.execute("""SELECT currentuser FROM currentuser""")
    currentuser = cur.fetchone()[0]
    cur.execute("""SELECT email FROM users WHERE username = (SELECT currentuser FROM currentuser)""")
    email = cur.fetchone()[0]
    current_user_credentials= {"name" : currentuser, "email" : email}
    msg = MIMEMultipart()
    msg["From"] = SENDER_ADDRESS
    msg["To"] = current_user_credentials['email']
    msg["Subject"] = 'Exported Posts'
    message = 'Here is the copy of your posts. Feel free to use this as backup to import later or store it for other reasons'
    msg.attach(MIMEText(message, "html"))

    with open('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/posts.csv','rb') as file:
        # Attach the file with filename to the email
            msg.attach(MIMEApplication(file.read(), Name='posts.csv'))
    s = smtplib.SMTP(host=SMTP_SERVER_HOST, port= SMTP_SERVER_PORT)
    s.starttls()
    s.login(SENDER_ADDRESS,SENDER_PASSWORD)
    s.send_message(msg)
    s.quit()
    return "Mail Sent"

@celery.task()
def import_posts():
    conn=sqlite3.connect("project.db")
    cur=conn.cursor()
    with open('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/posts.csv', mode ='r') as file:
        posts = csv.reader(file)
        cur.execute("""SELECT currentuser FROM currentuser""")
        currentuser = cur.fetchone()[0]
        #To prevent unsupported imports
        for rows in posts:
            if rows[0] == 'id':
                    continue 
            if rows[1] != currentuser:
                return "Import Failed"

    with open('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/posts.csv', mode ='r') as file:       
        cur.execute("""DELETE FROM POSTS WHERE username = (SELECT currentuser FROM currentuser)""")
        posts = csv.reader(file)
        for rows in posts:
                if rows[0] == 'id':
                    continue    
                query="""INSERT INTO POSTS VALUES (?,?,?,?)"""
                cur.execute(query,(int(rows[0]), rows[1], rows[2], rows[3]))
        conn.commit()
    return "Import Success"

@app.route("/export")
def export():
    result = export_posts.delay()
    return redirect(url_for('index'))

@app.route("/import", methods=['GET', 'POST'])
def upload():
    if request.method=="POST":
        fname ='posts.csv'
        f = request.files['file']
        f.save(secure_filename(fname))
        result = import_posts.delay()
        while not result.ready():
            time.sleep(0.5)
        if result.get() != "Import Success":
            return "<h1> Unsupported Import. Try logging in the correct account</h1> <a href='/login'>Go Back</a>"
        return redirect(url_for('index'))
    return render_template('import.html')

@app.route("/editpost/<id>", methods=['GET', 'POST'])
def editpost(id):
    print(id)
    if request.method=="POST":
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        
        try:
            dontreplaceimage = request.form['options']
        except:
            dontreplaceimage = "FALSE"
        try:
            dontreplacecaption = request.form['options2']
        except:
            dontreplacecaption = "FALSE"

        if request.files['img'].filename == '':
            if dontreplaceimage == "FALSE":
                return render_template("editpost.html")

        query="""SELECT username from posts WHERE id = ?"""
        cur.execute(query,(id,))
        username = cur.fetchone()[0]
        if dontreplaceimage == "FALSE":
            fname = id + '.jpg'
            os.remove('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/' + id + '.jpg')
            f = request.files['img']
            f.save(secure_filename(fname))
            shutil.move('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/' + fname , '/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/')

        if dontreplacecaption == "FALSE":
            caption=request.form['caption']
            query="""UPDATE posts SET caption = ? WHERE id = ? """
            cur.execute(query,(caption, id))
            conn.commit()
        return redirect('/profile/' + username)
    return render_template("editpost.html")

@app.route('/deletepost/<id>', methods=['GET', 'POST'])
def deletepost(id):
    if request.method == "POST":
        print(id)
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query1="""SELECT username FROM posts WHERE id = ?"""
        cur.execute(query1,(id,))
        username = cur.fetchone()[0]
        query="""DELETE FROM posts WHERE id = ? """
        cur.execute(query,(id,))
        conn.commit()
        os.remove('/mnt/d/Tanmay Bholane/Visual Studio Code/BLOG_LITE/static/' + id + '.jpg')
        return redirect('/profile/' + username)
    return render_template('deletepost.html')



#API's
class GetCurrentUser(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT currentuser FROM currentuser"""
        cur.execute(query)
        user = cur.fetchone()[0]
        return {'user' : user}

class GetPostInfo(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        cur.execute("""SELECT * FROM posts ORDER BY timestamp DESC""")
        rows = cur.fetchall()
        imglinks=[]
        usernames=[]
        pfplinks=[]
        captions=[]
        ids=[]
        for i in rows:
            imglink="/static/" + str(i[0]) + ".jpg"
            imglinks.append(imglink)
            pfplink = "/static/" + i[1] + ".jpg"
            pfplinks.append(pfplink)
            ids.append(i[0])
            usernames.append(i[1])
            captions.append(i[2])
        return {'posts_usernames' : usernames,'posts_pfplinks':pfplinks, 'posts_imglinks':imglinks,'posts_captions':captions, 'posts_ids' : ids}

class GetSearchResults(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT username FROM searchresults"""
        cur.execute(query)
        rows = cur.fetchall()
        usernames=[]
        links=[]
        for i in rows:
            usernames.append(i[0])
            link = "/static/" + i[0] + ".jpg"
            links.append(link)
        return {'usernames' : usernames, 'links' : links}

class Getpfp(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT username FROM requesteduser"""
        cur.execute(query)
        user = cur.fetchone()[0]
        srclink = "/static/" + user + ".jpg"
        return {'pfplink' : srclink, 'requested_user' : user}


class GetRequestedFollowers(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT follower FROM followings WHERE followee = (SELECT username FROM requesteduser) """
        cur.execute(query)
        output = cur.fetchall()
        followers=[]
        for i in output:
            followers.append(i[0])
        followings=[]
        cur.execute("""SELECT followee FROM followings WHERE follower = (SELECT username FROM requesteduser) """)
        output = cur.fetchall()
        for i in output:
            followings.append(i[0])
        cur.execute("""SELECT COUNT(id) FROM posts WHERE username = (SELECT username FROM requesteduser) """)
        posts = cur.fetchone()[0]
        return {'followers' : followers, 'followings' : followings, 'follower_count' : len(followers), 'following_count' : len(followings), 'posts' : posts}

class GetCurrentFollowers(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        query="""SELECT follower FROM followings WHERE followee = (SELECT currentuser FROM currentuser) """
        cur.execute(query)
        output = cur.fetchall()
        followers=[]
        for i in output:
            followers.append(i[0])
        followings=[]
        cur.execute("""SELECT followee FROM followings WHERE follower = (SELECT currentuser FROM currentuser) """)
        output = cur.fetchall()
        for i in output:
            followings.append(i[0])
        cur.execute("""SELECT COUNT(id) FROM posts WHERE username = (SELECT currentuser FROM currentuser) """)
        posts = cur.fetchone()[0]
        return {'followers' : followers, 'followings' : followings, 'follower_count' : len(followers), 'following_count' : len(followings), 'posts' : posts}

class GetBio(Resource):
    @token_required
    def get(self):
        conn=sqlite3.connect("project.db")
        cur=conn.cursor()
        cur.execute("""SELECT username FROM requesteduser""")
        user = cur.fetchone()[0]
        query="""SELECT bio FROM users WHERE username = ?"""
        cur.execute(query,(user,))
        bio = cur.fetchone()[0]
        return {'bio' : bio}


api.add_resource(GetCurrentUser, '/getcurrentuser')
api.add_resource(GetRequestedFollowers, '/getrequestedfollowers')
api.add_resource(GetCurrentFollowers, '/getcurrentfollowers')
api.add_resource(Getpfp, '/getpfp')
api.add_resource(GetSearchResults, '/getsearchresults')
api.add_resource(GetPostInfo, '/getpostinfo')
api.add_resource(GetBio, '/getbio')


if __name__=="__main__":
    app.run(debug=True, host = '0.0.0.0', port = 8080)