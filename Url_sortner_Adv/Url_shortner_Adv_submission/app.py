from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import string, random, validators
from pyngrok import ngrok

app = Flask(__name__, template_folder="/content/templates")
app.secret_key = "secret123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- DATABASE MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(9), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(500), nullable=False)
    short_code = db.Column(db.String(6), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# ---------------- LOGIN LOADER ----------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- UTILITY ----------------

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect("/dashboard")
        flash("Invalid username or password")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if len(username) < 5 or len(username) > 9:
            flash("Username must be between 5 to 9 characters long")
            return redirect("/signup")

        if User.query.filter_by(username=username).first():
            flash("This username already exists")
            return redirect("/signup")

        db.session.add(User(username=username, password=password))
        db.session.commit()
        flash("Signup successful. Please login.")
        return redirect("/")
    return render_template("signup.html")

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    short_url = None
    if request.method == "POST":
        original_url = request.form["original_url"]
        if validators.url(original_url):
            code = generate_short_code()
            db.session.add(URL(
                original_url=original_url,
                short_code=code,
                user_id=current_user.id
            ))
            db.session.commit()
            short_url = request.host_url + code
    urls = URL.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", short_url=short_url, urls=urls)

@app.route("/<code>")
def redirect_url(code):
    url = URL.query.filter_by(short_code=code).first_or_404()
    return redirect(url.original_url)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

# ---------------- RUN ----------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    public_url = ngrok.connect(5000)
    print("PUBLIC URL:", public_url)

    app.run(host="0.0.0.0", port=5000)
