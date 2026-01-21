from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import string, random, validators
from pyngrok import ngrok

app = Flask(__name__, template_folder="/content/templates212")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(500), nullable=False)
    short_code = db.Column(db.String(6), unique=True, nullable=False)

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/', methods=['GET', 'POST'])
def index():
    short_url = None
    error = None

    if request.method == 'POST':
        original_url = request.form['original_url']

        if not validators.url(original_url):
            error = "Invalid URL"
        else:
            short_code = generate_short_code()
            db.session.add(URL(original_url=original_url, short_code=short_code))
            db.session.commit()
            short_url = request.host_url + short_code

    return render_template("index.html", short_url=short_url, error=error)

@app.route('/<short_code>')
def redirect_url(short_code):
    url = URL.query.filter_by(short_code=short_code).first_or_404()
    return redirect(url.original_url)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    public_url = ngrok.connect(5000)
    print("PUBLIC URL:", public_url)

    app.run(host="0.0.0.0", port=5000, debug=False)
