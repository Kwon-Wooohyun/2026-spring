from flask import Flask
from models import db
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elladin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 최대 16MB
app.secret_key = 'elladin-secret-key'

db.init_app(app)

from routes import main
app.register_blueprint(main)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)