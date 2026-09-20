import os
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "spendsense_secret_key_2026"

DATABASE = "database.db"


# =========================================================
# GOOGLE OAUTH
# =========================================================

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db_connection()

    # -----------------------------------------------------
    # Users table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_picture TEXT,
            google_id TEXT,
            email_verified INTEGER DEFAULT 0,
            verification_code TEXT,
            verification_expiry TEXT,
            reset_token TEXT,
            reset_token_expiry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # Add missing columns for old database
    # -----------------------------------------------------

    existing_columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    new_columns = {
        "profile_picture": "TEXT",
        "google_id": "TEXT",
        "email_verified": "INTEGER DEFAULT 0",
        "verification_code": "TEXT",
        "verification_expiry": "TEXT",
        "reset_token": "TEXT",
        "reset_token_expiry": "TEXT"
    }

    for column, column_type in new_columns.items():

        if column not in existing_columns:

            conn.execute(
                f"ALTER TABLE users ADD COLUMN {column} {column_type}"
            )

    # -----------------------------------------------------
    # Unique Google ID
    # -----------------------------------------------------

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id
        ON users(google_id)
        WHERE google_id IS NOT NULL
    """)

    # -----------------------------------------------------
    # Categories table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # Transactions table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    # -----------------------------------------------------
    # Remove duplicate categories
    # -----------------------------------------------------

    conn.execute("""
        UPDATE transactions
        SET category_id = (
            SELECT MIN(c2.id)
            FROM categories c2
            WHERE c2.name = (
                SELECT c3.name
                FROM categories c3
                WHERE c3.id = transactions.category_id
            )
            AND c2.type = (
                SELECT c4.type
                FROM categories c4
                WHERE c4.id = transactions.category_id
            )
        )
        WHERE category_id IN (
            SELECT c.id
            FROM categories c
            WHERE c.id != (
                SELECT MIN(c2.id)
                FROM categories c2
                WHERE c2.name = c.name
                AND c2.type = c.type
            )
        )
    """)

    conn.execute("""
        DELETE FROM categories
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM categories
            GROUP BY name, type
        )
    """)

    # -----------------------------------------------------
    # Prevent duplicate categories in future
    # -----------------------------------------------------

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_categories_name_type
        ON categories(name, type)
    """)

    # -----------------------------------------------------
    # Default income categories
    # -----------------------------------------------------

    income_categories = [
        "Pocket Money",
        "Salary",
        "Scholarship",
        "Freelance",
        "Gift",
        "Other"
    ]

    # -----------------------------------------------------
    # Default expense categories
    # -----------------------------------------------------

    expense_categories = [
        "Food",
        "Travel",
        "Education",
        "Shopping",
        "Bills",
        "Entertainment",
        "Healthcare",
        "Other"
    ]

    # -----------------------------------------------------
    # Insert income categories
    # -----------------------------------------------------

    for category in income_categories:

        conn.execute(
            """
            INSERT OR IGNORE INTO categories
            (name, type)
            VALUES (?, ?)
            """,
            (category, "income")
        )

    # -----------------------------------------------------
    # Insert expense categories
    # -----------------------------------------------------

    for category in expense_categories:

        conn.execute(
            """
            INSERT OR IGNORE INTO categories
            (name, type)
            VALUES (?, ?)
            """,
            (category, "expense")
        )

    # -----------------------------------------------------
    # Budgets table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    # -----------------------------------------------------
    # Save and close
    # -----------------------------------------------------

    conn.commit()
    conn.close()

# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("home.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:

            flash("All fields are required.")
            return redirect(url_for("register"))

        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            flash("Email already registered.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, hashed_password)
        )

        conn.commit()
        conn.close()

        flash("Registration successful! Please login.")

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        # User does not exist
        if user is None:

            flash(
                "Invalid email or password.",
                "login_error"
            )

            return redirect(url_for("login"))

        # Wrong password
        if not check_password_hash(user["password"], password):

            flash(
                "Invalid email or password.",
                "login_error"
            )

            return redirect(url_for("login"))

        # Successful login
        session["user_id"] = user["id"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()

    # Total income
    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = ?
        AND type = 'income'
    """, (user_id,)).fetchone()[0]

    # Total expenses
    expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = ?
        AND type = 'expense'
    """, (user_id,)).fetchone()[0]

    # Balance
    balance = income - expenses

    # Savings percentage
    savings_percentage = 0

    if income > 0:
        savings_percentage = (balance / income) * 100

    # Recent transactions
    transactions = conn.execute("""
        SELECT
            transactions.*,
            categories.name AS category_name
        FROM transactions
        LEFT JOIN categories
        ON transactions.category_id = categories.id
        WHERE transactions.user_id = ?
        ORDER BY transactions.date DESC, transactions.id DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    # Spending by category
    spending_categories = conn.execute("""
        SELECT
            categories.name AS category_name,
            COALESCE(SUM(transactions.amount), 0) AS total
        FROM transactions
        JOIN categories
        ON transactions.category_id = categories.id
        WHERE transactions.user_id = ?
        AND transactions.type = 'expense'
        GROUP BY categories.id
        ORDER BY total DESC
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        balance=balance,
        income=income,
        expenses=expenses,
        savings_percentage=savings_percentage,
        transactions=transactions,
        spending_categories=spending_categories
    )
@app.route("/add-transaction", methods=["GET", "POST"])
def add_transaction():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    categories = conn.execute("""
        SELECT *
        FROM categories
        ORDER BY type, name
    """).fetchall()

    if request.method == "POST":

        transaction_type = request.form.get("type")
        amount = request.form.get("amount")
        category_id = request.form.get("category_id")
        description = request.form.get("description", "").strip()
        date = request.form.get("date")

        if not transaction_type or not amount or not category_id or not date:
            flash("Please fill in all required fields.")
            conn.close()
            return redirect(url_for("add_transaction"))

        try:
            amount = float(amount)

            if amount <= 0:
                flash("Amount must be greater than zero.")
                conn.close()
                return redirect(url_for("add_transaction"))

        except ValueError:
            flash("Please enter a valid amount.")
            conn.close()
            return redirect(url_for("add_transaction"))

        conn.execute("""
            INSERT INTO transactions
            (user_id, category_id, amount, type, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            category_id,
            amount,
            transaction_type,
            description,
            date
        ))

        conn.commit()
        conn.close()

        flash("Transaction added successfully!")

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template(
        "add_transaction.html",
        categories=categories
    )
# =========================================================
# TRANSACTIONS
# =========================================================

@app.route("/transactions")
def transactions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    transactions = conn.execute("""
        SELECT
            transactions.*,
            categories.name AS category_name
        FROM transactions
        LEFT JOIN categories
        ON transactions.category_id = categories.id
        WHERE transactions.user_id = ?
        ORDER BY transactions.date DESC, transactions.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "transactions.html",
        transactions=transactions
    )
# =========================================================
# DELETE TRANSACTION
# =========================================================

@app.route("/delete-transaction/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM transactions
        WHERE id = ?
        AND user_id = ?
    """, (
        transaction_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash("Transaction deleted successfully.")

    return redirect(url_for("transactions"))
@app.route("/edit-transaction/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    transaction = conn.execute("""
        SELECT *
        FROM transactions
        WHERE id = ?
        AND user_id = ?
    """, (
        transaction_id,
        session["user_id"]
    )).fetchone()

    if transaction is None:
        conn.close()
        flash("Transaction not found.")
        return redirect(url_for("transactions"))

    categories = conn.execute("""
        SELECT *
        FROM categories
        ORDER BY type, name
    """).fetchall()

    if request.method == "POST":

        transaction_type = request.form.get("type")
        amount = request.form.get("amount")
        category_id = request.form.get("category_id")
        description = request.form.get("description", "").strip()
        date = request.form.get("date")

        if not transaction_type or not amount or not category_id or not date:
            flash("Please fill in all required fields.")
            conn.close()
            return redirect(
                url_for(
                    "edit_transaction",
                    transaction_id=transaction_id
                )
            )

        try:
            amount = float(amount)

            if amount <= 0:
                flash("Amount must be greater than zero.")
                conn.close()
                return redirect(
                    url_for(
                        "edit_transaction",
                        transaction_id=transaction_id
                    )
                )

        except ValueError:
            flash("Please enter a valid amount.")
            conn.close()
            return redirect(
                url_for(
                    "edit_transaction",
                    transaction_id=transaction_id
                )
            )

        conn.execute("""
            UPDATE transactions
            SET
                category_id = ?,
                amount = ?,
                type = ?,
                description = ?,
                date = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            category_id,
            amount,
            transaction_type,
            description,
            date,
            transaction_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash("Transaction updated successfully!")
        return redirect(url_for("transactions"))

    conn.close()

    return render_template(
        "edit_transaction.html",
        transaction=transaction,
        categories=categories
    )
@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    expense_categories = conn.execute("""
        SELECT *
        FROM categories
        WHERE type = 'expense'
        ORDER BY name
    """).fetchall()

    if request.method == "POST":

        category_id = request.form.get("category_id")
        amount = request.form.get("amount")
        month = request.form.get("month")

        if not category_id or not amount or not month:
            flash("Please fill in all budget fields.")
            conn.close()
            return redirect(url_for("budgets"))

        try:
            amount = float(amount)

            if amount <= 0:
                flash("Budget amount must be greater than zero.")
                conn.close()
                return redirect(url_for("budgets"))

        except ValueError:
            flash("Please enter a valid budget amount.")
            conn.close()
            return redirect(url_for("budgets"))

        existing_budget = conn.execute("""
            SELECT id
            FROM budgets
            WHERE user_id = ?
            AND category_id = ?
            AND month = ?
        """, (
            session["user_id"],
            category_id,
            month
        )).fetchone()

        if existing_budget:
            conn.execute("""
                UPDATE budgets
                SET amount = ?
                WHERE id = ?
                AND user_id = ?
            """, (
                amount,
                existing_budget["id"],
                session["user_id"]
            ))
        else:
            conn.execute("""
                INSERT INTO budgets
                (user_id, category_id, amount, month)
                VALUES (?, ?, ?, ?)
            """, (
                session["user_id"],
                category_id,
                amount,
                month
            ))

        conn.commit()
        conn.close()

        flash("Budget saved successfully!")
        return redirect(url_for("budgets"))

    budgets_data = conn.execute("""
        SELECT
            budgets.id,
            budgets.amount,
            budgets.month,
            categories.name AS category_name
        FROM budgets
        LEFT JOIN categories
        ON budgets.category_id = categories.id
        WHERE budgets.user_id = ?
        ORDER BY budgets.month DESC, categories.name
    """, (
        session["user_id"],
    )).fetchall()

    budget_list = []

    for budget in budgets_data:

        spent = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE user_id = ?
            AND category_id = (
                SELECT category_id
                FROM budgets
                WHERE id = ?
            )
            AND type = 'expense'
            AND substr(date, 1, 7) = ?
        """, (
            session["user_id"],
            budget["id"],
            budget["month"]
        )).fetchone()[0]

        percentage = 0

        if budget["amount"] > 0:
            percentage = (spent / budget["amount"]) * 100

        if percentage > 100:
            percentage = 100

        remaining = budget["amount"] - spent

        budget_list.append({
            "id": budget["id"],
            "amount": budget["amount"],
            "month": budget["month"],
            "category_name": budget["category_name"],
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage
        })

    conn.close()

    return render_template(
        "budgets.html",
        categories=expense_categories,
        budgets=budget_list
    )
# =========================================================
# ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    user_id = session["user_id"]

    # -----------------------------------------------------
    # Category-wise expenses
    # -----------------------------------------------------

    category_data = conn.execute("""
        SELECT
            categories.name AS category_name,
            COALESCE(SUM(transactions.amount), 0) AS total
        FROM transactions
        JOIN categories
        ON transactions.category_id = categories.id
        WHERE transactions.user_id = ?
        AND transactions.type = 'expense'
        GROUP BY categories.id
        ORDER BY total DESC
    """, (user_id,)).fetchall()

    # -----------------------------------------------------
    # Monthly income and expenses
    # -----------------------------------------------------

    monthly_data = conn.execute("""
        SELECT
            substr(date, 1, 7) AS month,

            SUM(
                CASE
                    WHEN type = 'income' THEN amount
                    ELSE 0
                END
            ) AS income,

            SUM(
                CASE
                    WHEN type = 'expense' THEN amount
                    ELSE 0
                END
            ) AS expenses

        FROM transactions

        WHERE user_id = ?

        GROUP BY substr(date, 1, 7)

        ORDER BY month
    """, (user_id,)).fetchall()

    # -----------------------------------------------------
    # Total income
    # -----------------------------------------------------

    total_income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = ?
        AND type = 'income'
    """, (user_id,)).fetchone()[0]

    # -----------------------------------------------------
    # Total expenses
    # -----------------------------------------------------

    total_expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = ?
        AND type = 'expense'
    """, (user_id,)).fetchone()[0]

    conn.close()

    # -----------------------------------------------------
    # Prepare chart data
    # -----------------------------------------------------

    category_labels = [
        row["category_name"]
        for row in category_data
    ]

    category_values = [
        row["total"]
        for row in category_data
    ]

    monthly_labels = [
        row["month"]
        for row in monthly_data
    ]

    monthly_income = [
        row["income"] or 0
        for row in monthly_data
    ]

    monthly_expenses = [
        row["expenses"] or 0
        for row in monthly_data
    ]

    # -----------------------------------------------------
    # Render Analytics page
    # -----------------------------------------------------

    return render_template(
        "analytics.html",
        category_data=category_data,
        monthly_data=monthly_data,
        category_labels=category_labels,
        category_values=category_values,
        monthly_labels=monthly_labels,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        total_income=total_income,
        total_expenses=total_expenses
    )
@app.route("/delete-budget/<int:budget_id>", methods=["POST"])
def delete_budget(budget_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM budgets
        WHERE id = ?
        AND user_id = ?
    """, (
        budget_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash("Budget deleted successfully.")
    return redirect(url_for("budgets"))
# =========================================================
# CURRENT USER FOR ALL PAGES
# =========================================================

@app.context_processor
def inject_current_user():

    current_user = None

    if "user_id" in session:

        conn = get_db_connection()

        current_user = conn.execute("""
            SELECT id, name, email, profile_picture
            FROM users
            WHERE id = ?
        """, (session["user_id"],)).fetchone()

        conn.close()

    return {
        "current_user": current_user
    }
# =========================================================
# GOOGLE LOGIN
# =========================================================

@app.route("/google/login")
def google_login():

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    return google.authorize_redirect(redirect_uri)


# =========================================================
# GOOGLE CALLBACK
# =========================================================

@app.route("/google/callback")
def google_callback():

    try:

        token = google.authorize_access_token()

        userinfo = token.get("userinfo")

        if not userinfo:

            flash("Could not retrieve Google account information.")

            return redirect(url_for("login"))

        google_id = userinfo.get("sub")

        email = userinfo.get("email", "").strip().lower()

        name = userinfo.get("name") or email.split("@")[0]

        profile_picture = userinfo.get("picture")

        email_verified = bool(
            userinfo.get("email_verified")
        )

        # -------------------------------------------------
        # Make sure Google returned a verified email
        # -------------------------------------------------

        if not email or not email_verified:

            flash("Your Google email could not be verified.")

            return redirect(url_for("login"))

        conn = get_db_connection()

        # -------------------------------------------------
        # Check whether this Google account already exists
        # -------------------------------------------------

        user = conn.execute(
            "SELECT * FROM users WHERE google_id = ?",
            (google_id,)
        ).fetchone()

        # -------------------------------------------------
        # If Google ID doesn't exist, check email
        # -------------------------------------------------

        if not user:

            user = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            # ---------------------------------------------
            # Existing email/password account
            # ---------------------------------------------

            if user:

                conn.execute(
                    """
                    UPDATE users
                    SET google_id = ?,
                        profile_picture = ?,
                        email_verified = 1
                    WHERE id = ?
                    """,
                    (
                        google_id,
                        profile_picture,
                        user["id"]
                    )
                )

            # ---------------------------------------------
            # Completely new Google account
            # ---------------------------------------------

            else:

                conn.execute(
                    """
                    INSERT INTO users
                    (
                        name,
                        email,
                        password,
                        profile_picture,
                        google_id,
                        email_verified
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        "",
                        profile_picture,
                        google_id,
                        1
                    )
                )

        # -------------------------------------------------
        # Existing Google account
        # -------------------------------------------------

        else:

            conn.execute(
                """
                UPDATE users
                SET name = ?,
                    email = ?,
                    profile_picture = ?,
                    email_verified = 1
                WHERE id = ?
                """,
                (
                    name,
                    email,
                    profile_picture,
                    user["id"]
                )
            )

        conn.commit()

        # Get the latest user information

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        # -------------------------------------------------
        # Create Flask session
        # -------------------------------------------------

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["profile_picture"] = user["profile_picture"]

        return redirect(url_for("dashboard"))

    except Exception as e:

        print("Google Login Error:", e)

        flash(
            "Google login failed. Please try again."
        )

        return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check password match
        if new_password != confirm_password:
            flash("New password and confirm password do not match.")
            return redirect(url_for("forgot_password"))

        # Check password length
        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect(url_for("forgot_password"))

        conn = get_db_connection()

        # Find user
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user is None:
            conn.close()

            flash("No account found with this email address.")
            return redirect(url_for("forgot_password"))

        # Hash new password
        hashed_password = generate_password_hash(new_password)

        # Update password
        conn.execute(
            """
            UPDATE users
            SET password = ?
            WHERE email = ?
            """,
            (hashed_password, email)
        )

        conn.commit()
        conn.close()

        # IMPORTANT:
        # Successful password change → LOGIN
        flash("Password changed successfully. Please login with your new password.")

        return redirect(url_for("login"))

    return render_template("forgot_password.html")
# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )
@app.route("/manage-profile", methods=["GET", "POST"])
def manage_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        if not name:
            flash("Name cannot be empty.")
            conn.close()
            return redirect(url_for("manage_profile"))

        conn.execute("""
            UPDATE users
            SET name = ?
            WHERE id = ?
        """, (
            name,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash("Profile updated successfully!")
        return redirect(url_for("manage_profile"))

    conn.close()

    return render_template(
        "manage_profile.html",
        user=user
    )
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not subject or not message:
            flash("Please fill in all fields.")
            return redirect(url_for("contact"))

        # Contact message handling will be added here later.
        flash("Your message has been sent successfully!")

        return redirect(url_for("contact"))

    return render_template("contact.html")
# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)