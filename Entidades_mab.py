from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Tenant(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # Ex: "tenant_123"

class Arm(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    tenant_id = db.Column(db.String(50), db.ForeignKey('tenant.id'))
    name = db.Column(db.String(100))
    tenant = db.relationship('Tenant', backref='arms')

class BanditData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(50), db.ForeignKey('tenant.id'))
    profile_hash = db.Column(db.String(100))  # Inclui hora do dia (ex: "user_abc_morning")
    arm_id = db.Column(db.String(50), db.ForeignKey('arm.id'))
    pulls = db.Column(db.Integer, default=0)  # Quantas vezes o item foi mostrado
    rewards = db.Column(db.Integer, default=0)  # Quantas vezes foi clicado
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'profile_hash', 'arm_id'),
    )