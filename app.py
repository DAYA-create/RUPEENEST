from flask import Flask, render_template,render_template, request,redirect,session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

@app.route("/")
def home():
    return "Welcome to RupeeNest"

#registration route
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        cursor = mysql.connection.cursor()

        cursor.execute(
            """
            INSERT INTO users(name, email, password)
            VALUES(%s, %s, %s)
            """,
            (name, email, hashed_password)
        )

        mysql.connection.commit()

        cursor.close()

        return "Registration Successful!"

    return render_template("register.html")


#login route
from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        if user and check_password_hash(user[3], password):

            session["user"] = user[1]

            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("login.html")
#logout route
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")
#Dashboard route
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    return f"Welcome {session['user']} to RupeeNest Dashboard"

if __name__ == "__main__":
    app.run(debug=True)

