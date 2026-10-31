from datetime import datetime

from models.base import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(30))
    cpf_cnpj = db.Column(db.String(20))
    endereco = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ordens = db.relationship("OrdemServico", backref="cliente", lazy=True)

    def __repr__(self):
        return f"<Cliente {self.nome}>"
