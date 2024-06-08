from flask import Flask, render_template, url_for, redirect, session, request, send_file, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from forms import Adbanner, LoginForm
from flask_bootstrap import Bootstrap
from sqlalchemy import event
from flask_sqlalchemy import SQLAlchemy
import os
from bs4 import BeautifulSoup
from sklearn.exceptions import InconsistentVersionWarning
import requests
import re
from twilio.rest import Client
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import pickle
import warnings

URL = "https://www.cnet.com/ai-atlas/"

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)

class Adbanners(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    adbook_img = db.Column(db.String(250), nullable=False)
    adbook_name = db.Column(db.String(250), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

class Techupdate(db.Model):
    __tablename__ = "tech_update"
    id = db.Column(db.Integer, primary_key=True)
    headline = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()



# Twilio credentials
TWILIO_ACCOUNT_SID = 'AC382d9d01fea5283396ade921d7221947'
TWILIO_AUTH_TOKEN = '5b1fe2f96165b16a2b064bd679b04b7e'
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
MY_WHATSAPP_NUMBER = "whatsapp:+918618392082"
FRIEND_WHATSAPP_NUMBER = "whatsapp:+917795870380"

warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

# Load TF-IDF vectorizer and PassiveAggressiveClassifier
tfidf_vectorizer = TfidfVectorizer()
model = PassiveAggressiveClassifier()

# Load saved model and vectorizer
with open('model2.pkl', 'rb') as f:
    model = pickle.load(f)

with open('tfidfvect2.pkl', 'rb') as f:
    tfidf_vectorizer = pickle.load(f)

# Define functions
def preprocess_text(text):
    # Lowercase
    text = text.lower()
    # Remove special characters and digits
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Tokenize
    tokens = nltk.word_tokenize(text)
    # Remove stopwords and lemmatize
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    # Join tokens back into a string
    preprocessed_text = ' '.join(tokens)
    return preprocessed_text

def load_tracked_urls():
    tracked_urls = {item.link for item in Techupdate.query.all()}
    return tracked_urls

def predict(text):
    preprocessed_text = preprocess_text(text)
    vectorized_text = tfidf_vectorizer.transform([preprocessed_text])
    prediction = model.predict(vectorized_text)[0]
    return 'REAL' if prediction == 0 else 'FAKE'

def scrape_and_store():
    response = requests.get(URL)
    if response.status_code == 200:
        content = response.text
        soup = BeautifulSoup(content, "html.parser")

        blog_text = []
        blog_link = []

        tracked_urls = load_tracked_urls()

        blogs = soup.find_all("a", class_="c-storiesNeonHighlightsCard_link")

        if blogs:
            new_articles_found = False
            for blog in blogs:
                text = blog.get_text(strip=True)
                link = blog.get('href')
                full_link = f"https://www.cnet.com{link}"
                if text and link and full_link not in tracked_urls:
                    text = re.split(r'\d{1,2} (?:hour|hours|day|days) ago', text)[0].strip()
                    text = re.split(r'\d{1,2}:\d{2} • \s*\d{1,2} (?:hour|hours|day|days) ago', text)[0].strip()
                    blog_text.append(text)
                    blog_link.append(full_link)
                    new_articles_found = True

            if new_articles_found:
                for text, link in zip(blog_text, blog_link):
                    new_update = Techupdate(headline=text, link=link)
                    db.session.add(new_update)
                db.session.commit()
                send_whatsapp_message(blog_text, blog_link)
                return {"message": "New articles have been stored and sent via WhatsApp.", "status": "success"}
            else:
                return {"message": "Stay tuned, new news will come.", "status": "no_update"}
    return {"message": "Failed to retrieve the webpage.", "status": "error"}

def send_whatsapp_message(headlines, links):
    print("Sending WhatsApp message...")
    print(f"TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID}")
    print(f"TWILIO_AUTH_TOKEN: {TWILIO_AUTH_TOKEN}")
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message_body = "\n\n".join([f"{headline}: {link}" for headline, link in zip(headlines, links)])
    print("Message body:", message_body)

    try:
        # Send message to your number
        message1 = client.messages.create(
            body=message_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=MY_WHATSAPP_NUMBER
        )
        print("Message sent to your number:", message1.sid)

        # Send message to your friend's number
        message2 = client.messages.create(
            body=message_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=FRIEND_WHATSAPP_NUMBER
        )
        print("Message sent to friend's number:", message2.sid)

        return message1.sid, message2.sid
    except Exception as e:
        print("Error sending message:", e)
        return None


# ---------------------------------Home Route-------------------------- #

@app.route('/', methods=['GET'])
def home():
    banners = Adbanners.query.all()
    return render_template("index.html", banners=banners)


# ------------------------------------- Admin Route ----------------------------- #

@app.route('/admin', methods=['GET', 'POST'])
def admins():
    return render_template("admin.html")

# ------------------------------------- AD Banner ----------------------------- #

@app.route('/add_banner', methods=["GET", "POST"])
def adbanner():
    form = Adbanner()  # Instantiate the Adbanner form
    if form.validate_on_submit():
        new_adbook = Adbanners(
            adbook_img=form.adbookimage.data,
            adbook_name=form.adbookname.data
        )
        db.session.add(new_adbook)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("addbanner.html", form=form)

# ---------------------------------Login Route------------------------- #

@app.route('/login', methods=['GET', 'POST'])
def register_login():
    return render_template("login.html")


# ---------------------------------Predict------------------------- #


@app.route('/predict/', methods=['GET', 'POST'])
def predict_api():
    text = request.args.get("text")
    prediction = predict(text)
    return jsonify(prediction=prediction)


# ---------------------------------Scrape------------------------- #


@app.route('/scrape', methods=['GET'])
def scrape():
    result = scrape_and_store()  # Call the scraping function
    if result['status'] == 'success':
        flash(result['message'], 'success')
    elif result['status'] == 'no_update':
        flash(result['message'], 'info')
    else:
        flash(result['message'], 'error')
    return redirect(url_for('admins'))


# ---------------------------------Delete------------------------- #


@app.route('/delete_all', methods=['GET'])
def delete_all():
    try:
        num_rows_deleted = db.session.query(Techupdate).delete()
        db.session.commit()
        flash(f"All news entries deleted ({num_rows_deleted} rows).")
    except Exception as e:
        db.session.rollback()
        flash("Error occurred while trying to delete news entries.")
    return redirect(url_for('admins'))


# ---------------------------------WhatsApp-Connect------------------------- #


@app.route('/connect_whatsapp', methods=['GET'])
def connect_whatsapp():
    updates = Techupdate.query.limit(2).all()
    headlines = [update.headline for update in updates]
    links = [update.link for update in updates]
    if headlines and links:
        send_whatsapp_message(headlines, links)
        flash("Latest news sent to WhatsApp!")
    else:
        flash("No news to send.")
    return redirect(url_for('home'))


@app.route('/contact-us')
def contact():
    return render_template("contactUs.html")

@app.route('/newses')
def new():
    return render_template("blogs.html")

if __name__ == '__main__':
    app.run(debug=True)

