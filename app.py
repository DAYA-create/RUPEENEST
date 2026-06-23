from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL 
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import re
app = Flask(__name__)
app.secret_key = "rupeenest123"
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

        flash("Registration successful! Please login.")

        return redirect(url_for("login"))
    return render_template("register.html")

#login route

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
from datetime import date, datetime

def calculate_loan_interest(amount, rate, interest_type, start_date):
    if not start_date:
        return 0.0
    
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return 0.0
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
        
    today = date.today()
    elapsed_days = (today - start_date).days
    if elapsed_days <= 0:
        return 0.0
        
    rate_factor = float(rate) / 100.0
    principal = float(amount)
    
    if interest_type == 'daily':
        return round(principal * rate_factor * elapsed_days, 2)
    elif interest_type == 'weekly':
        return round(principal * rate_factor * (elapsed_days / 7.0), 2)
    elif interest_type == 'monthly':
        return round(principal * rate_factor * (elapsed_days / 30.0), 2)
    elif interest_type == 'yearly':
        return round(principal * rate_factor * (elapsed_days / 365.0), 2)
    else:
        return 0.0

@app.route("/dashboard")
def dashboard(): 
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM borrowers")
    total_borrowers = cursor.fetchone()[0]
    
    cursor.execute("SELECT amount, interest_rate, interest_type, start_date FROM loans WHERE status='active'")
    active_loans = cursor.fetchall()
    total_lent = sum(float(l[0]) for l in active_loans)
    
    total_interest = 0.0
    for l in active_loans:
        total_interest += calculate_loan_interest(l[0], l[1], l[2], l[3])
        
    cursor.execute("SELECT SUM(amount) FROM payments")
    total_collected_res = cursor.fetchone()[0]
    total_collected = float(total_collected_res) if total_collected_res else 0.0
    
    total_pending = round(total_lent + total_interest - total_collected, 2)
    
    cursor.close()
    
    return render_template(
        "dashboard.html",
        total_borrowers=total_borrowers,
        total_lent=round(total_lent, 2),
        total_interest=round(total_interest, 2),
        total_pending=total_pending
    )

#Borrowers route
@app.route('/borrowers')
def borrowers():

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM borrowers")

    borrowers = cursor.fetchall()

    cursor.close()

    return render_template(
        'borrowers.html',
        borrowers=borrowers
    )

# Add Borrower Route
@app.route('/add_borrower', methods=['GET', 'POST'])
def add_borrower():

    if request.method == 'POST':

        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        cursor = mysql.connection.cursor()

        cursor.execute(
            """
            INSERT INTO borrowers
            (name, phone, address)
            VALUES (%s, %s, %s)
            """,
            (name, phone, address)
        )

        mysql.connection.commit()

        cursor.close()

        return redirect('/borrowers')

    return render_template('add_borrower.html')

# Delete Borrower Route
@app.route('/delete_borrower/<int:id>')
def delete_borrower(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM borrowers WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    return redirect('/borrowers')

#returns borrower details when clicked
@app.route("/borrower/<int:id>")
def borrower_profile(id):
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT * FROM borrowers WHERE id=%s", (id,))
    borrower = cursor.fetchone()
    
    if not borrower:
        cursor.close()
        flash("Borrower not found.")
        return redirect("/borrowers")
        
    cursor.execute("SELECT id, amount, interest_rate, interest_type, start_date, status FROM loans WHERE borrower_id=%s ORDER BY start_date DESC", (id,))
    loans = cursor.fetchall()
    
    total_lent = 0.0
    total_interest = 0.0
    total_collected = 0.0
    
    loans_list = []
    for l in loans:
        cursor.execute("SELECT SUM(amount) FROM payments WHERE loan_id=%s", (l[0],))
        pmt_res = cursor.fetchone()[0]
        pmt_amount = float(pmt_res) if pmt_res else 0.0
        
        interest = calculate_loan_interest(l[1], l[2], l[3], l[4])
        balance = round(float(l[1]) + interest - pmt_amount, 2)
        
        loans_list.append({
            'id': l[0],
            'amount': float(l[1]),
            'interest_rate': float(l[2]),
            'interest_type': l[3],
            'start_date': l[4],
            'status': l[5],
            'interest': interest,
            'collected': pmt_amount,
            'balance': balance
        })
        
        if l[5] == 'active':
            total_lent += float(l[1])
            total_interest += interest
            total_collected += pmt_amount
            
    total_balance = round(total_lent + total_interest - total_collected, 2)
    
    cursor.close()
    
    return render_template(
        "borrower_profile.html",
        borrower=borrower,
        loans=loans_list,
        total_lent=round(total_lent, 2),
        total_collected=round(total_collected, 2),
        total_balance=total_balance
    )

# Add Loan Route
@app.route('/borrower/<int:borrower_id>/add_loan', methods=['GET', 'POST'])
def add_loan(borrower_id):
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM borrowers WHERE id=%s", (borrower_id,))
    borrower = cursor.fetchone()
    
    if not borrower:
        cursor.close()
        flash("Borrower not found.")
        return redirect("/borrowers")
        
    if request.method == 'POST':
        amount = request.form['amount']
        interest_rate = request.form['interest_rate']
        interest_type = request.form['interest_type']
        start_date = request.form['start_date']
        
        cursor.execute(
            """
            INSERT INTO loans (borrower_id, amount, interest_rate, interest_type, start_date, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            """,
            (borrower_id, amount, interest_rate, interest_type, start_date)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Loan added successfully!")
        return redirect(f"/borrower/{borrower_id}")
        
    cursor.close()
    return render_template('add_loan.html', borrower=borrower)

# Loan Details Route
@app.route('/loan/<int:loan_id>')
def loan_details(loan_id):
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT l.id, l.borrower_id, l.amount, l.interest_rate, l.interest_type, l.start_date, l.status, b.name 
        FROM loans l 
        JOIN borrowers b ON l.borrower_id = b.id 
        WHERE l.id=%s
    """, (loan_id,))
    loan = cursor.fetchone()
    
    if not loan:
        cursor.close()
        flash("Loan not found.")
        return redirect("/borrowers")
        
    accrued_interest = calculate_loan_interest(loan[2], loan[3], loan[4], loan[5])
    
    cursor.execute("SELECT id, amount, payment_date, notes FROM payments WHERE loan_id=%s ORDER BY payment_date DESC", (loan_id,))
    payments = cursor.fetchall()
    
    total_paid = sum(float(p[1]) for p in payments)
    total_outstanding = round(float(loan[2]) + accrued_interest - total_paid, 2)
    
    cursor.close()
    return render_template(
        'loan_details.html',
        loan=loan,
        accrued_interest=accrued_interest,
        payments=payments,
        total_paid=total_paid,
        total_outstanding=total_outstanding
    )

# Add Payment Route
@app.route('/loan/<int:loan_id>/add_payment', methods=['GET', 'POST'])
def add_payment(loan_id):
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT l.id, l.borrower_id, l.amount, l.interest_rate, l.interest_type, l.start_date, l.status, b.name 
        FROM loans l 
        JOIN borrowers b ON l.borrower_id = b.id 
        WHERE l.id=%s
    """, (loan_id,))
    loan = cursor.fetchone()
    
    if not loan:
        cursor.close()
        flash("Loan not found.")
        return redirect("/borrowers")
        
    if request.method == 'POST':
        amount = request.form['amount']
        payment_date = request.form['payment_date']
        notes = request.form['notes']
        
        cursor.execute(
            """
            INSERT INTO payments (loan_id, amount, payment_date, notes)
            VALUES (%s, %s, %s, %s)
            """,
            (loan_id, amount, payment_date, notes)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Payment recorded successfully!")
        return redirect(f"/loan/{loan_id}")
        
    cursor.close()
    return render_template('add_payment.html', loan=loan)

# Toggle Loan Status Route
@app.route('/loan/<int:loan_id>/toggle_status')
def toggle_loan_status(loan_id):
    if "user" not in session:
        return redirect("/login")
        
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, status, borrower_id FROM loans WHERE id=%s", (loan_id,))
    loan = cursor.fetchone()
    if not loan:
        cursor.close()
        flash("Loan not found.")
        return redirect("/borrowers")
        
    new_status = 'closed' if loan[1] == 'active' else 'active'
    cursor.execute("UPDATE loans SET status=%s WHERE id=%s", (new_status, loan_id))
    mysql.connection.commit()
    cursor.close()
    flash(f"Loan marked as {new_status}!")
    return redirect(f"/loan/{loan_id}")

if __name__ == "__main__":
    app.run(debug=True)

