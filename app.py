from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Job Application Tracker</h1><p>Your project is running.</p>"


if __name__ == "__main__":
    app.run(debug=True)