import random
from itertools import zip_longest


def listar_torneios(conexao):
    return conexao.execute(
        """
        SELECT t.*,
               COUNT(p.id) AS total_participantes
        FROM torneios t
        LEFT JOIN participantes p ON p.torneio_id = t.id
        GROUP BY t.id
        ORDER BY t.criado_em DESC, t.id DESC
        """
    ).fetchall()


def obter_torneio(conexao, torneio_id):
    return conexao.execute("SELECT * FROM torneios WHERE id = ?", (torneio_id,)).fetchone()


def listar_participantes(conexao, torneio_id):
    return conexao.execute(
        """
        SELECT *
        FROM participantes
        WHERE torneio_id = ?
        ORDER BY status ASC, derrotas ASC, nome COLLATE NOCASE
        """,
        (torneio_id,),
    ).fetchall()


def listar_partidas(conexao, torneio_id):
    return conexao.execute(
        """
        SELECT m.*,
               a.nome AS participante_a_nome,
               a.apelido AS participante_a_apelido,
               a.imagem AS participante_a_imagem,
               b.nome AS participante_b_nome,
               b.apelido AS participante_b_apelido,
               b.imagem AS participante_b_imagem,
               v.nome AS vencedor_nome,
               p.nome AS perdedor_nome
        FROM partidas m
        JOIN participantes a ON a.id = m.participante_a_id
        JOIN participantes b ON b.id = m.participante_b_id
        LEFT JOIN participantes v ON v.id = m.vencedor_id
        LEFT JOIN participantes p ON p.id = m.perdedor_id
        WHERE m.torneio_id = ?
        ORDER BY
            CASE m.chave
                WHEN 'upper' THEN 1
                WHEN 'lower' THEN 2
                ELSE 3
            END,
            m.rodada,
            m.ordem
        """,
        (torneio_id,),
    ).fetchall()


def criar_torneio(conexao, nome):
    cursor = conexao.execute("INSERT INTO torneios (nome) VALUES (?)", (nome.strip(),))
    return cursor.lastrowid


def adicionar_participante(conexao, torneio_id, nome, apelido="", imagem=None):
    conexao.execute(
        """
        INSERT INTO participantes (torneio_id, nome, apelido, imagem)
        VALUES (?, ?, ?, ?)
        """,
        (torneio_id, nome.strip(), apelido.strip(), imagem),
    )


def remover_participante(conexao, participante_id):
    conexao.execute("DELETE FROM participantes WHERE id = ?", (participante_id,))


def listar_imagens_participantes_torneio(conexao, torneio_id):
    linhas = conexao.execute(
        "SELECT imagem FROM participantes WHERE torneio_id = ? AND imagem IS NOT NULL",
        (torneio_id,),
    ).fetchall()
    return [linha["imagem"] for linha in linhas if linha["imagem"]]


def deletar_torneio(conexao, torneio_id):
    cursor = conexao.execute("DELETE FROM torneios WHERE id = ?", (torneio_id,))
    return cursor.rowcount > 0


def iniciar_torneio(conexao, torneio_id):
    participantes = conexao.execute(
        "SELECT id FROM participantes WHERE torneio_id = ? ORDER BY RANDOM()",
        (torneio_id,),
    ).fetchall()

    if len(participantes) < 2:
        raise ValueError("Cadastre pelo menos 2 participantes para iniciar o torneio.")

    if len(participantes) > 50:
        raise ValueError("O limite desta versao e de 50 participantes.")

    conexao.execute("DELETE FROM partidas WHERE torneio_id = ?", (torneio_id,))
    conexao.execute(
        """
        UPDATE participantes
        SET derrotas = 0, status = 'ativo'
        WHERE torneio_id = ?
        """,
        (torneio_id,),
    )
    conexao.execute(
        """
        UPDATE torneios
        SET status = 'andamento',
            upper_campeao_id = NULL,
            lower_campeao_id = NULL,
            primeiro_lugar_id = NULL,
            segundo_lugar_id = NULL,
            terceiro_lugar_id = NULL,
            iniciado_em = datetime('now', 'localtime'),
            finalizado_em = NULL
        WHERE id = ?
        """,
        (torneio_id,),
    )

    ids = [participante["id"] for participante in participantes]
    criar_partidas(conexao, torneio_id, "upper", 1, ids)
    recalcular_torneio(conexao, torneio_id)


def registrar_resultado(conexao, partida_id, vencedor_id):
    partida = conexao.execute("SELECT * FROM partidas WHERE id = ?", (partida_id,)).fetchone()
    if not partida:
        raise ValueError("Partida nao encontrada.")
    if partida["status"] == "finalizada":
        raise ValueError("Essa partida ja foi finalizada.")

    ids_partida = {partida["participante_a_id"], partida["participante_b_id"]}
    vencedor_id = int(vencedor_id)
    if vencedor_id not in ids_partida:
        raise ValueError("Vencedor invalido para esta partida.")

    perdedor_id = (
        partida["participante_b_id"]
        if vencedor_id == partida["participante_a_id"]
        else partida["participante_a_id"]
    )

    conexao.execute(
        """
        UPDATE partidas
        SET vencedor_id = ?,
            perdedor_id = ?,
            status = 'finalizada',
            finalizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (vencedor_id, perdedor_id, partida_id),
    )

    if partida["chave"] == "upper":
        registrar_derrota(conexao, perdedor_id)
    elif partida["chave"] == "lower":
        registrar_derrota(conexao, perdedor_id)
        talvez_guardar_terceiro_lugar(conexao, partida["torneio_id"], perdedor_id)
    elif partida["chave"] == "final":
        finalizar_podio(conexao, partida["torneio_id"], vencedor_id, perdedor_id)
        return

    recalcular_torneio(conexao, partida["torneio_id"])


def registrar_derrota(conexao, participante_id):
    participante = conexao.execute(
        "SELECT derrotas FROM participantes WHERE id = ?",
        (participante_id,),
    ).fetchone()
    derrotas = participante["derrotas"] + 1
    status = "eliminado" if derrotas >= 2 else "ativo"
    conexao.execute(
        "UPDATE participantes SET derrotas = ?, status = ? WHERE id = ?",
        (derrotas, status, participante_id),
    )


def recalcular_torneio(conexao, torneio_id):
    torneio = obter_torneio(conexao, torneio_id)
    if not torneio or torneio["status"] != "andamento":
        return

    if existem_partidas_pendentes(conexao, torneio_id, "upper"):
        return

    upper_campeao_id = torneio["upper_campeao_id"]
    if not upper_campeao_id:
        candidatos_upper = candidatos_por_derrotas(conexao, torneio_id, 0)
        if len(candidatos_upper) == 1:
            upper_campeao_id = candidatos_upper[0]
            conexao.execute(
                "UPDATE torneios SET upper_campeao_id = ? WHERE id = ?",
                (upper_campeao_id, torneio_id),
            )
        elif len(candidatos_upper) > 1 and not rodada_ja_existe_aberta(conexao, torneio_id, "upper"):
            rodada = proxima_rodada(conexao, torneio_id, "upper")
            criar_partidas(conexao, torneio_id, "upper", rodada, candidatos_upper)
            return

    if existem_partidas_pendentes(conexao, torneio_id, "lower"):
        return

    lower_campeao_id = obter_torneio(conexao, torneio_id)["lower_campeao_id"]
    candidatos_lower = candidatos_por_derrotas(conexao, torneio_id, 1)

    if upper_campeao_id and not lower_campeao_id and len(candidatos_lower) == 1:
        lower_campeao_id = candidatos_lower[0]
        conexao.execute(
            "UPDATE torneios SET lower_campeao_id = ? WHERE id = ?",
            (lower_campeao_id, torneio_id),
        )
        criar_grande_final(conexao, torneio_id, upper_campeao_id, lower_campeao_id)
        return

    if len(candidatos_lower) > 1 and not rodada_ja_existe_aberta(conexao, torneio_id, "lower"):
        rodada = proxima_rodada(conexao, torneio_id, "lower")
        criar_partidas(conexao, torneio_id, "lower", rodada, candidatos_lower)


def criar_partidas(conexao, torneio_id, chave, rodada, participantes_ids):
    ids = list(participantes_ids)
    random.shuffle(ids)
    if len(ids) < 2:
        return

    pares = list(zip_longest(ids[0::2], ids[1::2]))
    ordem = 1
    for participante_a_id, participante_b_id in pares:
        if participante_b_id is None:
            continue
        conexao.execute(
            """
            INSERT INTO partidas (
                torneio_id, chave, rodada, ordem, participante_a_id, participante_b_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (torneio_id, chave, rodada, ordem, participante_a_id, participante_b_id),
        )
        ordem += 1


def criar_grande_final(conexao, torneio_id, upper_campeao_id, lower_campeao_id):
    existe = conexao.execute(
        "SELECT id FROM partidas WHERE torneio_id = ? AND chave = 'final'",
        (torneio_id,),
    ).fetchone()
    if existe:
        return

    conexao.execute(
        """
        INSERT INTO partidas (
            torneio_id, chave, rodada, ordem, participante_a_id, participante_b_id
        )
        VALUES (?, 'final', 1, 1, ?, ?)
        """,
        (torneio_id, upper_campeao_id, lower_campeao_id),
    )


def finalizar_podio(conexao, torneio_id, vencedor_id, perdedor_id):
    torneio = obter_torneio(conexao, torneio_id)
    terceiro_id = torneio["terceiro_lugar_id"]
    if not terceiro_id:
        terceiro = conexao.execute(
            """
            SELECT id
            FROM participantes
            WHERE torneio_id = ? AND status = 'eliminado' AND id NOT IN (?, ?)
            ORDER BY derrotas DESC, id DESC
            LIMIT 1
            """,
            (torneio_id, vencedor_id, perdedor_id),
        ).fetchone()
        terceiro_id = terceiro["id"] if terceiro else None

    conexao.execute(
        """
        UPDATE torneios
        SET status = 'finalizado',
            primeiro_lugar_id = ?,
            segundo_lugar_id = ?,
            terceiro_lugar_id = ?,
            finalizado_em = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (vencedor_id, perdedor_id, terceiro_id, torneio_id),
    )


def talvez_guardar_terceiro_lugar(conexao, torneio_id, perdedor_id):
    torneio = obter_torneio(conexao, torneio_id)
    if torneio["terceiro_lugar_id"]:
        return

    participantes_com_uma_derrota = candidatos_por_derrotas(conexao, torneio_id, 1)
    if torneio["upper_campeao_id"] and len(participantes_com_uma_derrota) == 1:
        conexao.execute(
            "UPDATE torneios SET terceiro_lugar_id = ? WHERE id = ?",
            (perdedor_id, torneio_id),
        )


def candidatos_por_derrotas(conexao, torneio_id, derrotas):
    linhas = conexao.execute(
        """
        SELECT id
        FROM participantes
        WHERE torneio_id = ? AND derrotas = ? AND status = 'ativo'
        ORDER BY id
        """,
        (torneio_id, derrotas),
    ).fetchall()
    return [linha["id"] for linha in linhas]


def existem_partidas_pendentes(conexao, torneio_id, chave):
    return (
        conexao.execute(
            """
            SELECT COUNT(*) AS total
            FROM partidas
            WHERE torneio_id = ? AND chave = ? AND status = 'pendente'
            """,
            (torneio_id, chave),
        ).fetchone()["total"]
        > 0
    )


def rodada_ja_existe_aberta(conexao, torneio_id, chave):
    return existem_partidas_pendentes(conexao, torneio_id, chave)


def proxima_rodada(conexao, torneio_id, chave):
    rodada = conexao.execute(
        """
        SELECT COALESCE(MAX(rodada), 0) + 1 AS proxima
        FROM partidas
        WHERE torneio_id = ? AND chave = ?
        """,
        (torneio_id, chave),
    ).fetchone()
    return rodada["proxima"]


def buscar_nome_participante(conexao, participante_id):
    if not participante_id:
        return None
    participante = conexao.execute(
        "SELECT nome, apelido, imagem FROM participantes WHERE id = ?",
        (participante_id,),
    ).fetchone()
    return participante
