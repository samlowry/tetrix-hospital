from datetime import datetime
from .user import db

class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    holder_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow) 