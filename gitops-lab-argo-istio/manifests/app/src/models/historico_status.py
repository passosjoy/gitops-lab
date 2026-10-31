from datetime import datetime

from models.base import db


class HistoricoStatus(db.Model):
    __tablename__ = "historico_status"

    id = db.Column(db.Integer, primary_key=True)
    os_id = db.Column(db.Integer, db.ForeignKey("ordens_servico.id"), nullable=False)
    status_anterior = db.Column(db.String(30))
    status_novo = db.Column(db.String(30))
    usuario = db.Column(db.String(80))
    motivo = db.Column(db.String(255))
    registrado_em = db.Column(db.DateTime, default=datetime.utcnow)
