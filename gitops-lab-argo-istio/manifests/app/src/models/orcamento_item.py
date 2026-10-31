from models.base import db


class OrcamentoItem(db.Model):
    __tablename__ = "orcamento_itens"

    id = db.Column(db.Integer, primary_key=True)
    os_id = db.Column(db.Integer, db.ForeignKey("ordens_servico.id"), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20))  # PECA / MAO_DE_OBRA
    quantidade = db.Column(db.Integer, default=1)
    valor_unitario = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)

    def calcular_total(self):
        self.valor_total = (self.quantidade or 0) * (self.valor_unitario or 0.0)
        return self.valor_total
