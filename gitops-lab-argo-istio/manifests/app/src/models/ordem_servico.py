from datetime import datetime, date

from models.base import db


class OrdemServico(db.Model):
    __tablename__ = "ordens_servico"

    id = db.Column(db.Integer, primary_key=True)
    numero_os = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    veiculo_marca = db.Column(db.String(80))
    veiculo_modelo = db.Column(db.String(80))
    placa = db.Column(db.String(10))
    km = db.Column(db.Integer)
    sintoma = db.Column(db.Text)
    status = db.Column(db.String(30), default="AGUARDANDO_ORCAMENTO", index=True)
    responsavel = db.Column(db.String(80))
    valor_orcamento = db.Column(db.Float, default=0.0)
    valor_final = db.Column(db.Float, default=0.0)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao_orcamento = db.Column(db.DateTime)
    data_inicio_execucao = db.Column(db.DateTime)
    data_finalizacao = db.Column(db.DateTime)
    data_emissao_nota = db.Column(db.DateTime)
    data_entrega = db.Column(db.DateTime)
    dias_para_entrega = db.Column(db.Integer)
    observacao = db.Column(db.Text)

    itens_orcamento = db.relationship(
        "OrcamentoItem", backref="ordem_servico", lazy=True, cascade="all, delete-orphan"
    )
    nota = db.relationship("NotaServico", backref="ordem_servico", uselist=False)
    historico = db.relationship("HistoricoStatus", backref="ordem_servico", lazy=True)

    def calcular_dias_para_entrega(self):
        if self.data_entrada and self.data_entrega:
            d1 = self.data_entrada.date() if isinstance(self.data_entrada, datetime) else self.data_entrada
            d2 = self.data_entrega.date() if isinstance(self.data_entrega, datetime) else self.data_entrega
            if isinstance(d1, datetime):
                d1 = d1.date()
            if isinstance(d2, datetime):
                d2 = d2.date()
            self.dias_para_entrega = (d2 - d1).days
            return self.dias_para_entrega
        return None

    def __repr__(self):
        return f"<OS {self.numero_os} {self.status}>"
