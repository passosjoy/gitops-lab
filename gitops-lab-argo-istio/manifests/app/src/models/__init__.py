from models.base import db
from models.cliente import Cliente
from models.ordem_servico import OrdemServico
from models.orcamento_item import OrcamentoItem
from models.nota_servico import NotaServico
from models.historico_status import HistoricoStatus

__all__ = ["db", "Cliente", "OrdemServico", "OrcamentoItem", "NotaServico", "HistoricoStatus"]
