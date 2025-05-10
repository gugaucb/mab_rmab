from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime # Não é mais usado diretamente aqui se get_time_bin está em recommender

db = SQLAlchemy()

class Tenant(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))

class Arm(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    tenant_id = db.Column(db.String(50), db.ForeignKey('tenant.id'))
    name = db.Column(db.String(100))
    tenant = db.relationship('Tenant', backref=db.backref('arms', lazy=True)) # lazy=True é uma boa prática

class BanditData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String(50), db.ForeignKey('tenant.id'))
    profile_hash = db.Column(db.String(100))  # Contexto do usuário + tempo
    arm_id = db.Column(db.String(50), db.ForeignKey('arm.id'))
    position = db.Column(db.Integer)  # Posição do arm na lista recomendada (1, 2, ..., K)
    pulls = db.Column(db.Integer, default=0)
    rewards = db.Column(db.Integer, default=0)
    
    # Relacionamentos para facilitar queries (opcional, mas útil)
    tenant = db.relationship('Tenant')
    arm = db.relationship('Arm')

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'profile_hash', 'arm_id', 'position'),
    )