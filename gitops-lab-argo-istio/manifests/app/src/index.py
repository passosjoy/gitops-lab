import logging
import os
import platform
import random
from datetime import datetime, date
from functools import wraps
from urllib.parse import quote_plus

from ddtrace import tracer
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.exceptions import HTTPException
from flask_migrate import Migrate, upgrade
from sqlalchemy import text

from models.base import db
from models import Cliente, OrdemServico, OrcamentoItem, NotaServico, HistoricoStatus
from observability import (
    ENV,
    FAULT_MODE,
    FAULT_RATE,
    LAB_ENABLED,
    LAB_TOKEN,
    SERVICE,
    VERSION,
    after_request as obs_after_request,
    before_request as obs_before_request,
    fault_active,
    gauge,
    histogram,
    incr,
    init_metrics,
    setup_logging,
    start_background_faults,
    tag_current_span_error,
)

setup_logging()
init_metrics()

app = Flask(
    __name__,
    static_url_path="",
    static_folder="static",
    template_folder="templates",
)

app.logger.handlers = list(logging.getLogger().handlers)
app.logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
app.logger.propagate = False

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me-oficina-rasta")

app_info = {
    "version": VERSION,
    "platform": platform.system(),
    "python_version": platform.python_version(),
}

db_host = os.getenv("DB_HOST", "localhost")
db_user = os.getenv("DB_USER", "oficina")
db_password = os.getenv("DB_PASSWORD", "oficina")
db_name = os.getenv("DB_NAME", "oficina")
db_port = os.getenv("DB_PORT", "5432")
db_sslmode = os.getenv("DB_SSLMODE", "").strip()

db_url = (
    f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_password)}"
    f"@{db_host}:{db_port}/{db_name}"
)
if db_sslmode:
    db_url += f"?sslmode={db_sslmode}"

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    "pool_timeout": 10,
}

db.init_app(app)
migrate = Migrate(app, db)

app.before_request(obs_before_request)
app.after_request(obs_after_request)

_faults_started = False


@app.before_request
def _start_faults_once():
    global _faults_started
    if not _faults_started and FAULT_MODE != "none":
        _faults_started = True
        start_background_faults()


def lab_guard(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not LAB_ENABLED:
            abort(404)
        if LAB_TOKEN and request.headers.get("X-Lab-Token") != LAB_TOKEN:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def gerar_numero_os():
    ano = datetime.now().year
    count = OrdemServico.query.count() + 1
    return f"OS-{ano}-{count:06d}"


def gerar_numero_nota():
    count = NotaServico.query.count() + 1
    return f"NS-{count:06d}"


def registrar_historico(os_obj, status_anterior, status_novo, usuario="sistema", motivo=None):
    hist = HistoricoStatus(
        os_id=os_obj.id,
        status_anterior=status_anterior,
        status_novo=status_novo,
        usuario=usuario,
        motivo=motivo,
    )
    db.session.add(hist)


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    if isinstance(exc, HTTPException):
        return exc.get_response()
    tag_current_span_error(exc)
    app.logger.error("Erro não tratado", exc_info=exc)
    return {"error": "internal_error"}, 500


@app.route("/")
def painel():
    with tracer.trace("oficina.painel", resource="GET /") as span:
        hoje = date.today()
        os_abertas = OrdemServico.query.filter_by(status="AGUARDANDO_ORCAMENTO").count()
        orcamento = OrdemServico.query.filter_by(status="ORCAMENTO_ENVIADO").count()
        em_execucao = OrdemServico.query.filter_by(status="EM_EXECUCAO").count()
        aguardando_nota = OrdemServico.query.filter_by(status="AGUARDANDO_NOTA").count()
        entregues_hoje = OrdemServico.query.filter(
            OrdemServico.status == "ENTREGUE",
            OrdemServico.data_entrega >= datetime.combine(hoje, datetime.min.time()),
        ).count()

        em_execucao_lista = OrdemServico.query.filter_by(status="EM_EXECUCAO").all()
        em_atraso = 0
        for os in em_execucao_lista:
            if os.data_entrada:
                dias = (datetime.utcnow() - os.data_entrada).days
                if dias > 7:
                    em_atraso += 1

        entregues_7 = OrdemServico.query.filter(
            OrdemServico.status == "ENTREGUE",
            OrdemServico.data_entrega >= datetime.combine(date(hoje.year, hoje.month, max(1, hoje.day - 7)), datetime.min.time()),
        ).all()
        media_dias = 0
        if entregues_7:
            soma = sum([o.dias_para_entrega or 0 for o in entregues_7])
            media_dias = round(soma / len(entregues_7), 1)

        gauge("oficina.os.em_execucao", em_execucao)

        span.set_tag("os.abertas", os_abertas)
        span.set_tag("os.em_execucao", em_execucao)
        span.set_tag("os.atraso", em_atraso)

    return render_template(
        "painel.html",
        os_abertas=os_abertas,
        orcamento=orcamento,
        em_execucao=em_execucao,
        aguardando_nota=aguardando_nota,
        entregues_hoje=entregues_hoje,
        em_atraso=em_atraso,
        media_dias=media_dias,
    )


@app.route("/clientes")
def clientes_list():
    clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template("clientes/lista.html", clientes=clientes)


@app.route("/clientes/novo", methods=["GET", "POST"])
def clientes_novo():
    if request.method == "POST":
        cliente = Cliente(
            nome=request.form.get("nome"),
            telefone=request.form.get("telefone"),
            cpf_cnpj=request.form.get("cpf_cnpj"),
            endereco=request.form.get("endereco"),
        )
        db.session.add(cliente)
        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("clientes_list"))
    return render_template("clientes/novo.html")


@app.route("/os")
def os_lista():
    status = request.args.get("status")
    query = OrdemServico.query
    if status:
        query = query.filter_by(status=status)
    ordens = query.order_by(OrdemServico.data_entrada.desc()).all()
    return render_template("os/lista.html", ordens=ordens)


@app.route("/os/nova", methods=["GET", "POST"])
@tracer.wrap(name="oficina.os.entrada", resource="POST /os/nova")
def os_nova():
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        cliente = Cliente.query.get_or_404(cliente_id)
        numero_os = gerar_numero_os()
        os_obj = OrdemServico(
            numero_os=numero_os,
            cliente_id=cliente.id,
            veiculo_marca=request.form.get("veiculo_marca"),
            veiculo_modelo=request.form.get("veiculo_modelo"),
            placa=request.form.get("placa"),
            km=request.form.get("km") or None,
            sintoma=request.form.get("sintoma"),
            status="AGUARDANDO_ORCAMENTO",
            responsavel=request.form.get("responsavel"),
        )
        db.session.add(os_obj)
        registrar_historico(os_obj, None, "AGUARDANDO_ORCAMENTO")
        db.session.commit()
        incr("oficina.os.entrada", {"loja": "lanternagem_do_rasta"})
        app.logger.info(
            "os_entrada",
            extra={"os_numero": numero_os, "cliente_id": cliente.id, "placa": os_obj.placa},
        )
        flash(f"OS {numero_os} aberta com sucesso!", "success")
        return redirect(url_for("os_detalhe", os_id=os_obj.id))
    clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template("os/nova.html", clientes=clientes)


@app.route("/os/<int:os_id>")
def os_detalhe(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    return render_template("os/detalhe.html", os=os_obj)


@app.route("/os/<int:os_id>/orcamento", methods=["GET", "POST"])
@tracer.wrap(name="oficina.orcamento.enviar", resource="POST /os/<id>/orcamento")
def os_orcamento(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    if request.method == "POST":
        OrcamentoItem.query.filter_by(os_id=os_obj.id).delete()
        total = 0.0
        descricoes = request.form.getlist("descricao[]")
        tipos = request.form.getlist("tipo[]")
        quantidades = request.form.getlist("quantidade[]")
        valores = request.form.getlist("valor_unitario[]")
        for desc, tipo, qtd, val in zip(descricoes, tipos, quantidades, valores):
            if not desc:
                continue
            qtd_i = int(qtd or 1)
            val_f = float(val or 0)
            item = OrcamentoItem(
                os_id=os_obj.id,
                descricao=desc,
                tipo=tipo or "PECA",
                quantidade=qtd_i,
                valor_unitario=val_f,
                valor_total=qtd_i * val_f,
            )
            db.session.add(item)
            total += item.valor_total
        status_anterior = os_obj.status
        os_obj.valor_orcamento = total
        os_obj.status = "ORCAMENTO_ENVIADO"
        registrar_historico(os_obj, status_anterior, "ORCAMENTO_ENVIADO")
        db.session.commit()
        incr("oficina.orcamento.enviado", {"loja": "lanternagem_do_rasta"})
        app.logger.info("orcamento_enviado", extra={"os_numero": os_obj.numero_os, "valor_orcamento": total})
        flash("Orçamento enviado para aprovação!", "success")
        return redirect(url_for("os_detalhe", os_id=os_obj.id))
    return render_template("orcamento/form.html", os=os_obj)


@app.route("/os/<int:os_id>/aprovar", methods=["POST"])
@tracer.wrap(name="oficina.orcamento.aprovar", resource="POST /os/<id>/aprovar")
def os_aprovar(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    status_anterior = os_obj.status
    os_obj.status = "APROVADO"
    os_obj.data_aprovacao_orcamento = datetime.utcnow()
    registrar_historico(os_obj, status_anterior, "APROVADO")
    db.session.commit()
    incr("oficina.orcamento.aprovado", {"loja": "lanternagem_do_rasta"})
    app.logger.info("orcamento_aprovado", extra={"os_numero": os_obj.numero_os})
    flash("Orçamento aprovado! Iniciar execução.", "success")
    return redirect(url_for("os_detalhe", os_id=os_obj.id))


@app.route("/os/<int:os_id>/recusar", methods=["POST"])
@tracer.wrap(name="oficina.orcamento.recusar", resource="POST /os/<id>/recusar")
def os_recusar(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    motivo = request.form.get("motivo")
    status_anterior = os_obj.status
    os_obj.status = "RECUSADO"
    registrar_historico(os_obj, status_anterior, "RECUSADO", motivo=motivo)
    db.session.commit()
    incr("oficina.orcamento.recusado", {"loja": "lanternagem_do_rasta"})
    app.logger.info("orcamento_recusado", extra={"os_numero": os_obj.numero_os, "motivo": motivo})
    flash("Orçamento recusado.", "warning")
    return redirect(url_for("os_detalhe", os_id=os_obj.id))


@app.route("/os/<int:os_id>/execucao/iniciar", methods=["POST"])
@tracer.wrap(name="oficina.execucao.iniciar", resource="POST /os/<id>/execucao/iniciar")
def os_execucao_iniciar(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    status_anterior = os_obj.status
    os_obj.status = "EM_EXECUCAO"
    os_obj.data_inicio_execucao = datetime.utcnow()
    registrar_historico(os_obj, status_anterior, "EM_EXECUCAO")
    db.session.commit()
    gauge("oficina.os.em_execucao", OrdemServico.query.filter_by(status="EM_EXECUCAO").count())
    app.logger.info("execucao_iniciada", extra={"os_numero": os_obj.numero_os})
    flash("Execução iniciada!", "success")
    return redirect(url_for("os_detalhe", os_id=os_obj.id))


@app.route("/os/<int:os_id>/execucao/finalizar", methods=["POST"])
@tracer.wrap(name="oficina.execucao.finalizar", resource="POST /os/<id>/execucao/finalizar")
def os_execucao_finalizar(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    status_anterior = os_obj.status
    os_obj.status = "AGUARDANDO_NOTA"
    os_obj.data_finalizacao = datetime.utcnow()
    total = os_obj.valor_orcamento
    if not total:
        total = sum(i.valor_total for i in os_obj.itens_orcamento)
    os_obj.valor_final = total
    registrar_historico(os_obj, status_anterior, "AGUARDANDO_NOTA")
    db.session.commit()
    incr("oficina.os.finalizado", {"loja": "lanternagem_do_rasta"})
    gauge("oficina.os.em_execucao", OrdemServico.query.filter_by(status="EM_EXECUCAO").count())
    app.logger.info("os_finalizado", extra={"os_numero": os_obj.numero_os, "valor_final": total})
    flash("Trabalho finalizado! Emitir nota simulada.", "success")
    return redirect(url_for("os_detalhe", os_id=os_obj.id))


@app.route("/os/<int:os_id>/nota", methods=["GET", "POST"])
@tracer.wrap(name="oficina.nota.emitir", resource="POST /os/<id>/nota")
def os_nota(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    if request.method == "POST":
        if os_obj.nota:
            flash("Nota já emitida para esta OS.", "warning")
            return redirect(url_for("os_detalhe", os_id=os_obj.id))
        numero_nota = gerar_numero_nota()
        valor = os_obj.valor_final or os_obj.valor_orcamento
        nota = NotaServico(
            os_id=os_obj.id,
            numero_nota=numero_nota,
            serie="A1",
            valor_servicos=valor,
            valor_total=valor,
            emitida_em=datetime.utcnow(),
            chave_simulada="".join([random.choice("0123456789ABCDEF") for _ in range(44)]),
        )
        db.session.add(nota)
        os_obj.status = "AGUARDANDO_ENTREGA"
        os_obj.data_emissao_nota = datetime.utcnow()
        registrar_historico(os_obj, "AGUARDANDO_NOTA", "AGUARDANDO_ENTREGA")
        db.session.commit()
        incr("oficina.nota.emitida", {"loja": "lanternagem_do_rasta"})
        app.logger.info("nota_emitida", extra={"os_numero": os_obj.numero_os, "numero_nota": numero_nota})
        flash(f"Nota {numero_nota} emitida (simulada)!", "success")
        return redirect(url_for("os_detalhe", os_id=os_obj.id))
    valor = os_obj.valor_final or os_obj.valor_orcamento
    return render_template("nota/form.html", os=os_obj, valor=valor)


@app.route("/os/<int:os_id>/entrega", methods=["POST"])
@tracer.wrap(name="oficina.entrega.finalizar", resource="POST /os/<id>/entrega")
def os_entrega(os_id):
    os_obj = OrdemServico.query.get_or_404(os_id)
    status_anterior = os_obj.status
    os_obj.status = "ENTREGUE"
    os_obj.data_entrega = datetime.utcnow()
    dias = os_obj.calcular_dias_para_entrega()
    valor = os_obj.valor_final or os_obj.valor_orcamento
    registrar_historico(os_obj, status_anterior, "ENTREGUE")
    db.session.commit()
    incr("oficina.os.entregue", {"loja": "lanternagem_do_rasta"})
    histogram("oficina.dias.para.entrega", float(dias) if dias is not None else 0, {"loja": "lanternagem_do_rasta", "aprovado": "sim"})
    gauge("oficina.valor.medio_os", float(valor), {"loja": "lanternagem_do_rasta"})
    app.logger.info(
        "os_entregue",
        extra={
            "os_numero": os_obj.numero_os,
            "cliente_id": os_obj.cliente_id,
            "placa": os_obj.placa,
            "dias_para_entrega": dias,
            "valor_final": valor,
        },
    )
    flash(f"Veículo entregue! Dias para entrega: {dias} dia(s).", "success")
    return redirect(url_for("os_detalhe", os_id=os_obj.id))


@app.route("/health")
def health():
    return {"status": "healthy", "service": SERVICE, "env": ENV, "version": VERSION}, 200


@app.route("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}, 200
    except Exception as exc:
        app.logger.error("Readiness falhou", exc_info=exc)
        return {"status": "not_ready", "database": "unavailable"}, 503


@app.route("/version")
def version():
    return {"service": SERVICE, "env": ENV, "version": VERSION}, 200


@app.route("/metrics")
def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


app.logger.info("Oficina de Lanternagem e Pintura do Rasta inicializada", extra={"service": SERVICE})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
