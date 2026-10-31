from datetime import datetime

from models.base import db


class NotaServico(db.Model):
    __tablename__ = "nota_servico"

    id = db.Column(db.Integer, primary_key=True)
    os_id = db.Column(db.Integer, db.ForeignKey("ordens_servico.id"), nullable=False)
    numero_nota = db.Column(db.String(20), unique=True)
    serie = db.Column(db.String(10), default="A1")
    valor_servicos = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)
    emitida_em = db.Column(db.DateTime, default=datetime.utcnow)
    chave_simulada = db.Column(db.String(44))
