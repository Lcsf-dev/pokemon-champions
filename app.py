from datetime import datetime
from pathlib import Path
from threading import Timer
from uuid import uuid4
import webbrowser

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from banco import RAIZ_PROJETO, iniciar_banco, obter_conexao
from torneio_servico import (
    adicionar_participante,
    deletar_torneio,
    buscar_nome_participante,
    criar_torneio,
    iniciar_torneio,
    listar_imagens_participantes_torneio,
    listar_participantes,
    listar_partidas,
    listar_torneios,
    obter_torneio,
    registrar_resultado,
    remover_participante,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = "torneio-pokemon-local"
app.config["UPLOAD_FOLDER"] = RAIZ_PROJETO / "static" / "uploads" / "participantes"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif"}
PORTA_LOCAL = 5000


def extensao_permitida(nome_arquivo):
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def salvar_imagem(arquivo):
    if not arquivo or not arquivo.filename or not extensao_permitida(arquivo.filename):
        return None

    nome_seguro = secure_filename(arquivo.filename)
    extensao = nome_seguro.rsplit(".", 1)[1].lower()
    nome_final = f"{uuid4().hex}.{extensao}"
    caminho_destino = Path(app.config["UPLOAD_FOLDER"]) / nome_final
    arquivo.save(caminho_destino)
    return f"uploads/participantes/{nome_final}"


def localizar_logo():
    pasta_static = RAIZ_PROJETO / "static"
    for nome_logo in ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "logo.gif", "logo.svg"):
        caminho_logo = pasta_static / nome_logo
        if caminho_logo.exists():
            return nome_logo
    return None


def localizar_favicon():
    pasta_static = RAIZ_PROJETO / "static"
    for nome_favicon in ("favicon.ico", "pokebola.png", "logo.ico"):
        caminho_favicon = pasta_static / nome_favicon
        if caminho_favicon.exists():
            return nome_favicon
    return localizar_logo()


def converter_data_hora(valor):
    if not valor:
        return None

    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def formatar_data_hora(valor):
    data_hora = converter_data_hora(valor)
    if not data_hora:
        return None
    return data_hora.strftime("%d/%m/%Y %H:%M")


def formatar_hora(valor):
    data_hora = converter_data_hora(valor)
    if not data_hora:
        return None
    return data_hora.strftime("%H:%M")


@app.context_processor
def variaveis_globais():
    return {
        "caminho_logo": localizar_logo(),
        "caminho_favicon": localizar_favicon(),
        "versao_assets": "20260908-periodo-torneio",
        "formatar_data_hora": formatar_data_hora,
        "formatar_hora": formatar_hora,
    }
def abrir_navegador():
    webbrowser.open_new(f"http://127.0.0.1:{PORTA_LOCAL}")



@app.route("/favicon.ico")
def favicon():
    resposta = send_from_directory(RAIZ_PROJETO / "static", "favicon.ico", mimetype="image/x-icon")
    resposta.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resposta.headers["Pragma"] = "no-cache"
    resposta.headers["Expires"] = "0"
    return resposta


def apagar_imagens_participantes(imagens):
    pasta_static = (RAIZ_PROJETO / "static").resolve()

    for imagem in imagens:
        caminho_imagem = (pasta_static / imagem).resolve()
        if pasta_static not in caminho_imagem.parents:
            continue
        if caminho_imagem.exists() and caminho_imagem.is_file():
            caminho_imagem.unlink()

def montar_chaves_visuais(partidas):
    chaves = {
        "upper": {},
        "lower": {},
        "final": {},
    }

    for partida in partidas:
        chave = partida["chave"]
        rodada = partida["rodada"]
        if chave not in chaves:
            chaves[chave] = {}
        if rodada not in chaves[chave]:
            chaves[chave][rodada] = []
        chaves[chave][rodada].append(partida)

    return {
        chave: [
            {"numero": rodada, "partidas": partidas_rodada}
            for rodada, partidas_rodada in sorted(rodadas.items())
        ]
        for chave, rodadas in chaves.items()
    }

@app.route("/")
def inicio():
    with obter_conexao() as conexao:
        torneios = listar_torneios(conexao)
    return render_template("inicio.html", torneios=torneios)


@app.post("/torneios")
def criar():
    nome = request.form.get("nome", "").strip()
    if not nome:
        flash("Informe um nome para o torneio.", "erro")
        return redirect(url_for("inicio"))

    with obter_conexao() as conexao:
        torneio_id = criar_torneio(conexao, nome)
        conexao.commit()
    flash("Torneio criado com sucesso.", "sucesso")
    return redirect(url_for("participantes", torneio_id=torneio_id))


@app.post("/torneios/<int:torneio_id>/deletar")
def deletar(torneio_id):
    with obter_conexao() as conexao:
        torneio_atual = obter_torneio(conexao, torneio_id)
        if not torneio_atual:
            flash("Torneio não encontrado.", "erro")
            return redirect(url_for("inicio"))

        imagens = listar_imagens_participantes_torneio(conexao, torneio_id)
        deletar_torneio(conexao, torneio_id)
        conexao.commit()

    apagar_imagens_participantes(imagens)
    flash(f"Torneio '{torneio_atual['nome']}' excluído com sucesso.", "sucesso")
    return redirect(url_for("inicio"))

@app.route("/torneios/<int:torneio_id>/participantes")
def participantes(torneio_id):
    with obter_conexao() as conexao:
        torneio = obter_torneio(conexao, torneio_id)
        lista = listar_participantes(conexao, torneio_id)
    return render_template("participantes.html", torneio=torneio, participantes=lista)


@app.post("/torneios/<int:torneio_id>/participantes")
def adicionar(torneio_id):
    nome = request.form.get("nome", "").strip()
    apelido = request.form.get("apelido", "").strip()
    imagem = salvar_imagem(request.files.get("imagem"))

    if not nome:
        flash("Informe o nome do participante.", "erro")
        return redirect(url_for("participantes", torneio_id=torneio_id))

    with obter_conexao() as conexao:
        total = len(listar_participantes(conexao, torneio_id))
        if total >= 50:
            flash("Limite de 50 participantes atingido.", "erro")
        else:
            adicionar_participante(conexao, torneio_id, nome, apelido, imagem)
            conexao.commit()
            flash("Participante cadastrado.", "sucesso")
    return redirect(url_for("participantes", torneio_id=torneio_id))


@app.post("/participantes/<int:participante_id>/remover")
def remover(participante_id):
    torneio_id = int(request.form.get("torneio_id"))
    with obter_conexao() as conexao:
        remover_participante(conexao, participante_id)
        conexao.commit()
    flash("Participante removido.", "sucesso")
    return redirect(url_for("participantes", torneio_id=torneio_id))


@app.post("/torneios/<int:torneio_id>/iniciar")
def iniciar(torneio_id):
    try:
        with obter_conexao() as conexao:
            iniciar_torneio(conexao, torneio_id)
            conexao.commit()
        flash("Chaves sorteadas. O torneio começou!", "sucesso")
        return redirect(url_for("torneio", torneio_id=torneio_id))
    except ValueError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("participantes", torneio_id=torneio_id))


@app.route("/torneios/<int:torneio_id>")
def torneio(torneio_id):
    with obter_conexao() as conexao:
        torneio_atual = obter_torneio(conexao, torneio_id)
        participantes_lista = listar_participantes(conexao, torneio_id)
        partidas = listar_partidas(conexao, torneio_id)
        podio = {
            "primeiro": buscar_nome_participante(conexao, torneio_atual["primeiro_lugar_id"]),
            "segundo": buscar_nome_participante(conexao, torneio_atual["segundo_lugar_id"]),
            "terceiro": buscar_nome_participante(conexao, torneio_atual["terceiro_lugar_id"]),
        }
    return render_template(
        "torneio.html",
        torneio=torneio_atual,
        participantes=participantes_lista,
        partidas=partidas,
        podio=podio,
    )



@app.route("/torneios/<int:torneio_id>/chaves")
def chaves(torneio_id):
    with obter_conexao() as conexao:
        torneio_atual = obter_torneio(conexao, torneio_id)
        partidas = listar_partidas(conexao, torneio_id)

    return render_template(
        "chaves.html",
        torneio=torneio_atual,
        chaves=montar_chaves_visuais(partidas),
    )

@app.post("/partidas/<int:partida_id>/resultado")
def resultado(partida_id):
    torneio_id = int(request.form.get("torneio_id"))
    vencedor_id = request.form.get("vencedor_id")
    if not vencedor_id:
        flash("Selecione um vencedor para registrar o resultado.", "erro")
        return redirect(url_for("torneio", torneio_id=torneio_id))

    try:
        with obter_conexao() as conexao:
            registrar_resultado(conexao, partida_id, vencedor_id)
            conexao.commit()
        flash("Resultado registrado e salvo.", "sucesso")
    except ValueError as erro:
        flash(str(erro), "erro")
    return redirect(url_for("torneio", torneio_id=torneio_id))


if __name__ == "__main__":
    iniciar_banco()
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Timer(1.0, abrir_navegador).start()
    app.run(host="127.0.0.1", port=PORTA_LOCAL, debug=False, use_reloader=False)
