import sqlite3
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parent
CAMINHO_BANCO = RAIZ_PROJETO / "torneio.db"


def obter_conexao():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def iniciar_banco():
    with obter_conexao() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS torneios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'cadastro',
                upper_campeao_id INTEGER,
                lower_campeao_id INTEGER,
                primeiro_lugar_id INTEGER,
                segundo_lugar_id INTEGER,
                terceiro_lugar_id INTEGER,
                iniciado_em TEXT,
                finalizado_em TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (upper_campeao_id) REFERENCES participantes(id),
                FOREIGN KEY (lower_campeao_id) REFERENCES participantes(id),
                FOREIGN KEY (primeiro_lugar_id) REFERENCES participantes(id),
                FOREIGN KEY (segundo_lugar_id) REFERENCES participantes(id),
                FOREIGN KEY (terceiro_lugar_id) REFERENCES participantes(id)
            );

            CREATE TABLE IF NOT EXISTS participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                torneio_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                apelido TEXT,
                imagem TEXT,
                derrotas INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ativo',
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (torneio_id) REFERENCES torneios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS partidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                torneio_id INTEGER NOT NULL,
                chave TEXT NOT NULL,
                rodada INTEGER NOT NULL,
                ordem INTEGER NOT NULL,
                participante_a_id INTEGER NOT NULL,
                participante_b_id INTEGER NOT NULL,
                vencedor_id INTEGER,
                perdedor_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pendente',
                criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finalizada_em TEXT,
                FOREIGN KEY (torneio_id) REFERENCES torneios(id) ON DELETE CASCADE,
                FOREIGN KEY (participante_a_id) REFERENCES participantes(id),
                FOREIGN KEY (participante_b_id) REFERENCES participantes(id),
                FOREIGN KEY (vencedor_id) REFERENCES participantes(id),
                FOREIGN KEY (perdedor_id) REFERENCES participantes(id)
            );

            CREATE TABLE IF NOT EXISTS historico_torneios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                torneio_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                dados TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (torneio_id) REFERENCES torneios(id) ON DELETE CASCADE
            );
            """
        )
        garantir_coluna(conexao, "torneios", "iniciado_em", "TEXT")
        garantir_coluna(conexao, "torneios", "finalizado_em", "TEXT")
        preencher_datas_torneios_existentes(conexao)


def garantir_coluna(conexao, tabela, coluna, tipo):
    colunas = conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    if coluna not in {linha["name"] for linha in colunas}:
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def preencher_datas_torneios_existentes(conexao):
    conexao.execute(
        """
        UPDATE torneios
        SET iniciado_em = (
            SELECT MIN(criada_em)
            FROM partidas
            WHERE partidas.torneio_id = torneios.id
        )
        WHERE iniciado_em IS NULL
          AND status != 'cadastro'
          AND EXISTS (
            SELECT 1
            FROM partidas
            WHERE partidas.torneio_id = torneios.id
        )
        """
    )
    conexao.execute(
        """
        UPDATE torneios
        SET finalizado_em = (
            SELECT MAX(finalizada_em)
            FROM partidas
            WHERE partidas.torneio_id = torneios.id
              AND finalizada_em IS NOT NULL
        )
        WHERE finalizado_em IS NULL
          AND status = 'finalizado'
          AND EXISTS (
            SELECT 1
            FROM partidas
            WHERE partidas.torneio_id = torneios.id
              AND finalizada_em IS NOT NULL
        )
        """
    )
