import json
import pymysql
import jwt
import requests
from app import app
from db_config import mysql
from flask import jsonify
from flask import flash, request, session, make_response, render_template, Response
from functools import wraps
from flask_cors import CORS
import datetime

CORS(app)

def check_for_token(param):
    @wraps(param)
    def wrapped(*args, **kwargs):
        token = ""
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
        if not token:
            return jsonify({"message": "Missing Token"}), 403
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"])
            # can use this data to fetch current user with contact number encoded in token
        except:
            return jsonify({"message": "Invalid Token"}), 403
        return param(*args, **kwargs)

    return wrapped

@app.route("/api/authenticate", methods=["POST"])
def login():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        email = request.json["Email"]
        password = request.json["Password"]
        check = cur.execute(
            "SELECT user_id, email FROM users WHERE ( email = '"
            + str(email)
            + "' AND password= '"+ str(password)
            +"');"
        )
        if check:
            records = cur.fetchone()
            user_id = records["user_id"]
            token = jwt.encode(
                {
                    "user_id": user_id,
                    "exp": datetime.datetime.utcnow()
                    + datetime.timedelta(minutes=43200),
                },
                app.config["SECRET_KEY"],
            )

            resp = jsonify({"token": token.decode("utf-8")})
            resp.status_code = 200
            return resp
        else:
          emptyarray = {"followings":[]}
          emptyarrayf = {"followers":[]}
          cur.execute(
          "Insert into users (email,password,follows,followers) VALUES ('"
          + str(email)
          + "','"
          + str(password)
          + "','"+ json.dumps(emptyarray)
          + "','"+ json.dumps(emptyarrayf)
          + "' );"
          )
          conn.commit()  
          if cur:   
              token = jwt.encode(
                  {
                      "user_id": cur.lastrowid,
                      "exp": datetime.datetime.utcnow()
                      + datetime.timedelta(minutes=43200),
                  },
                  app.config["SECRET_KEY"],
              )

              resp = jsonify({"token": token.decode("utf-8")})
              resp.status_code = 200
              return resp
          
          resp = jsonify({"message": "Error."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/user", methods=["GET"])
@check_for_token
def userdetails():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]
        check = cur.execute(
            "SELECT user_id, email, follows, followers FROM users WHERE ( user_id = '"
            + str(token_user_id)
            +"');"
        )
        if check:
            records = cur.fetchone()
            user_id = records["user_id"]
            email = records["email"]
            follows = json.loads(records["follows"])
            followers = json.loads(records["followers"])

            resp = jsonify({"email": email, "user_id":user_id, "follows": len(follows["followings"]), "followers":len(followers["followers"])})
            resp.status_code = 200
            return resp
        else:
          resp = jsonify({"message": "Details not found/ user might have been deleted."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/follow/<id>", methods=["POST"])
@check_for_token
def follow(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur2 = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]
        check = cur.execute(
            "SELECT user_id, email, follows FROM users WHERE ( user_id = '"
            + str(token_user_id)
            +"');"
        )
        if check:
            records = cur.fetchone()
            checkfollow_user = cur.execute(
            "SELECT user_id, followers FROM users WHERE ( user_id = '"
            + str(id)
            +"');"
            )
            if checkfollow_user:
                user_records = cur.fetchone()
                # details of authorized user.
                follows = json.loads(records["follows"])

                #details of user to be followed.
                followers = json.loads(user_records["followers"])
                
                if token_user_id in followers["followers"]:
                    resp = jsonify({"message": "Already followed."})
                    resp.status_code = 403
                    return resp
                else:
                    follows["followings"].append(id)
                    followers["followers"].append(token_user_id)

                    cur.execute("UPDATE users SET follows = '"+json.dumps(follows)+
                    "' WHERE user_id = "+str(token_user_id)+" ;")
                    conn.commit()

                    cur.execute("UPDATE users SET followers = '"+json.dumps(followers)+
                    "' WHERE user_id = "+str(id)+" ;")
                    conn.commit()

                    if cur and cur2:
                        resp = jsonify({"message": "{} followed {} successfully.".format(token_user_id, id)})
                        resp.status_code = 200
                        return resp
            else:
                resp = jsonify({"message": "Follow unsuccessful, user not found."})
                resp.status_code = 403
                return resp
        else:
          resp = jsonify({"message": "Invalid user."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        cur2.close()
        conn.close()

@app.route("/api/unfollow/<id>", methods=["POST"])
@check_for_token
def unfollow(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur2 = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]
        check = cur.execute(
            "SELECT user_id, email, follows FROM users WHERE ( user_id = '"
            + str(token_user_id)
            +"');"
        )
        if check:
            records = cur.fetchone()
            # details of authorized user.
            follows = json.loads(records["follows"])

            if token_user_id not in follows["followings"]:
                resp = jsonify({"message": "User not followed."})
                resp.status_code = 403
                return resp


            checkunfollow_user = cur.execute(
            "SELECT user_id, followers FROM users WHERE ( user_id = '"
            + str(id)
            +"');"
            )

            if checkunfollow_user:
                user_records = cur.fetchone()
                #details of user to be followed.
                followers = json.loads(user_records["followers"])

                follows["followings"].remove(id)
                followers["followers"].remove(token_user_id)

                cur.execute("UPDATE users SET follows = '"+json.dumps(follows)+
                "' WHERE user_id = "+str(token_user_id)+" ;")
                conn.commit()

                cur.execute("UPDATE users SET followers = '"+json.dumps(followers)+
                "' WHERE user_id = "+str(id)+" ;")
                conn.commit()

                if cur and cur2:
                    resp = jsonify({"message": "{} unfollowed {} successfully.".format(token_user_id, id)})
                    resp.status_code = 200
                    return resp
            else:
                resp = jsonify({"message": "Unfollow request unsuccessful, user not found."})
                resp.status_code = 403
                return resp
        else:
          resp = jsonify({"message": "Invalid user."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        cur2.close()
        conn.close()

@app.route("/api/posts", methods=["POST"])
@check_for_token
def addposts():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]

        Title = request.json["Title"]
        Description = request.json["Description"]
        cur.execute(
          "Insert into posts (title,descr,created_by) VALUES ('"
          + str(Title)
          + "','"
          + str(Description)
          + "','"
          + str(token_user_id)
          + "');"
          )
        conn.commit()  

        if cur:  
            check = cur.execute(
            "SELECT * FROM posts WHERE ( id = '"
            + str(cur.lastrowid)
            +"');"
            )
            if check:
                records = cur.fetchone()

            resp = jsonify({"message": "Post added successfully.", "details":records})
            resp.status_code = 200
            return resp 

        resp = jsonify({"message": "Error."})
        resp.status_code = 403
        return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/posts/<id>", methods=["GET","DELETE"])
@check_for_token
def posts(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]

        check = cur.execute(
        "SELECT * FROM posts WHERE ( id = '"
        + str(id)
        +"');"
        )
        if check:
            records = cur.fetchone()
            if request.method == "DELETE":
                cur.execute(
                "DELETE FROM posts WHERE id = '"
                + str(id)
                + "' and created_by = "+str(token_user_id)+";"
                )
                conn.commit()
                if cur:
                    resp = jsonify({"message": "Post deleted successfully.", })
                    resp.status_code = 200
                    return resp 
                resp = jsonify({"message": "Error, Post doesn't belong to you."})
                resp.status_code = 403
                return resp

            elif request.method == "GET":
                # getting likes count
                check = cur.execute(
                "SELECT COUNT(id) FROM likes WHERE ( post_id = '"
                + str(cur.lastrowid)
                +"');"
                )
                likes_records = cur.fetchone()
                # getting comments count
                check = cur.execute(
                "SELECT COUNT(comment_id) FROM comments WHERE ( post_id = '"
                + str(id)
                +"');"
                )
                comments_records = cur.fetchone()

                records["comments"] = comments_records["COUNT(comment_id)"]
                records["likes"] = likes_records["COUNT(id)"]
        
                resp = jsonify({"details":records})
                resp.status_code = 200
                return resp 

        resp = jsonify({"message": "Invalid post ID."})
        resp.status_code = 403
        return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/all_posts", methods=["GET"])
@check_for_token
def allposts():
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]

        check = cur.execute(
        "SELECT * FROM posts WHERE created_by = "
        + str(token_user_id)
        +" ORDER BY created_at DESC;"
        )
        if check:
            post_records = cur.fetchall()
            for i in range(0,len(post_records)):
                post_id = post_records[i]["id"]

                # getting likes count
                check = cur.execute(
                "SELECT COUNT(id) FROM likes WHERE ( post_id = '"
                + str(post_id)
                +"');"
                )
                likes_records = cur.fetchone()

                # getting comments 
                check = cur.execute(
                "SELECT * FROM comments WHERE ( post_id = '"
                + str(post_id)
                +"');"
                )
                comments_records = cur.fetchall()

                post_records[i]["comments"] = comments_records
                post_records[i]["likes"] = likes_records["COUNT(id)"]

            resp = jsonify({"posts": post_records})
            resp.status_code = 200
            return resp
        resp = jsonify({"message": "No posts found."})
        resp.status_code = 403
        return resp

    finally:
        cur.close()
        conn.close()
    
@app.route("/api/like/<id>", methods=["POST"])
@check_for_token
def like(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]

        check = cur.execute(
            "SELECT * FROM posts WHERE ( id = '"
            + str(id)
            +"');"
        )
        if check:
            cur.execute(
            "SELECT * FROM likes WHERE post_id = "
            + str(id)
            +" AND user_id = "+str(token_user_id)+";"
            )
            user_records = cur.fetchone()
            
            if user_records is None:
                cur.execute(
                "Insert into likes (post_id,user_id) VALUES ("
                + str(id)
                + ","
                + str(token_user_id)
                + ");"
                )
                conn.commit()  

                if cur:  
                    resp = jsonify({"message": "Liked Successfully."})
                    resp.status_code = 200
                    return resp
                resp = jsonify({"message": "Error occured."})
                resp.status_code = 403
                return resp
                
                    
            resp = jsonify({"message": "Already Liked."})
            resp.status_code = 403
            return resp
        else:
          resp = jsonify({"message": "Invalid Post ID."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/unlike/<id>", methods=["POST"])
@check_for_token
def unlike(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]

        check = cur.execute(
            "SELECT * FROM posts WHERE ( id = '"
            + str(id)
            +"');"
        )
        if check:
            cur.execute(
            "SELECT * FROM likes WHERE post_id = '"
            + str(id)
            +"' AND user_id = "+str(token_user_id)+";"
            )

            user_records = cur.fetchone()
            if user_records:
                    cur.execute(
                    "DELETE FROM likes WHERE post_id = '"
                    + str(id)
                    + "' AND user_id = '"
                    + str(token_user_id)
                    + "';"
                    )
                    conn.commit()  

                    if cur:  
                        resp = jsonify({"message": "Unliked Successfully."})
                        resp.status_code = 200
                        return resp
                    resp = jsonify({"message": "Error occured."})
                    resp.status_code = 403
                    return resp
                
            resp = jsonify({"message": "Post is not liked, yet."})
            resp.status_code = 403
            return resp
        else:
          resp = jsonify({"message": "Invalid Post ID."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        conn.close()

@app.route("/api/comment/<id>", methods=["POST"])
@check_for_token
def comment(id):
    conn = mysql.connect()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        token = request.headers['Authorization']
        token_data = jwt.decode(token, app.config['SECRET_KEY'])
        token_user_id = token_data["user_id"]
        comments = request.json["comment"]

        check = cur.execute(
            "SELECT * FROM posts WHERE ( id = '"
            + str(id)
            +"');"
        )
        if check:
            cur.execute(
            "Insert into comments (post_id,user_id,comment) VALUES ('"
            + str(id)
            + "','"
            + str(token_user_id)
            + "','"
            + str(comments)
            + "');"
            )
            conn.commit()  

            if cur:  
                resp = jsonify({"Comment-ID": cur.lastrowid})
                resp.status_code = 200
                return resp
            resp = jsonify({"message": "Error occured."})
            resp.status_code = 403
            return resp
                
        else:
          resp = jsonify({"message": "Invalid Post ID."})
          resp.status_code = 403
          return resp

    finally:
        cur.close()
        conn.close()

@app.route("/")
def home():
    resp = jsonify({"message": "Hello."})
    resp.status_code = 200
    return resp


@app.errorhandler(404)
def not_found(error=None):
    message = {
        "status": 404,
        "message": "Not Found " + request.url,
    }

    resp = jsonify(message)
    resp.status_code = 404
    return resp

if __name__ == "__main__":
  app.run(host="localhost", port=5000, debug=True)
