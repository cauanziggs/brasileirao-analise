"""Funções reutilizáveis para carregar, limpar e analisar os dados do Brasileirão."""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "campeonato-brasileiro-full.csv"


def carregar_dados(caminho: Path = DATA_PATH) -> pd.DataFrame:
    """Lê o CSV bruto e devolve um DataFrame limpo, com colunas derivadas.

    Colunas criadas:
        temporada   -> ano da temporada (a de 2020 terminou em fev/2021)
        gols_total  -> gols somados na partida
        resultado   -> 'Mandante', 'Empate' ou 'Visitante'
    """
    df = pd.read_csv(caminho)

    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["arena"] = df["arena"].str.strip()

    # A temporada 2020 foi concluída em janeiro/fevereiro de 2021 (pandemia).
    df["temporada"] = df["data"].dt.year
    df.loc[(df["temporada"] == 2021) & (df["data"] < "2021-03-01"), "temporada"] = 2020

    df = df.rename(columns={"mandante_Placar": "gols_mandante", "visitante_Placar": "gols_visitante"})
    df["gols_total"] = df["gols_mandante"] + df["gols_visitante"]

    df["resultado"] = np.select(
        [df["gols_mandante"] > df["gols_visitante"], df["gols_mandante"] < df["gols_visitante"]],
        ["Mandante", "Visitante"],
        default="Empate",
    )

    return df.sort_values(["data", "ID"]).reset_index(drop=True)


def formato_longo(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma 1 linha por jogo em 1 linha por time por jogo (visão de cada clube)."""
    casa = pd.DataFrame(
        {
            "ID": df["ID"], "data": df["data"], "temporada": df["temporada"], "rodada": df["rodata"],
            "time": df["mandante"], "adversario": df["visitante"], "local": "Casa",
            "gols_pro": df["gols_mandante"], "gols_contra": df["gols_visitante"],
        }
    )
    fora = pd.DataFrame(
        {
            "ID": df["ID"], "data": df["data"], "temporada": df["temporada"], "rodada": df["rodata"],
            "time": df["visitante"], "adversario": df["mandante"], "local": "Fora",
            "gols_pro": df["gols_visitante"], "gols_contra": df["gols_mandante"],
        }
    )
    longo = pd.concat([casa, fora], ignore_index=True)
    longo["pontos"] = np.select(
        [longo["gols_pro"] > longo["gols_contra"], longo["gols_pro"] == longo["gols_contra"]],
        [3, 1],
        default=0,
    )
    longo["vitoria"] = (longo["pontos"] == 3).astype(int)
    longo["empate"] = (longo["pontos"] == 1).astype(int)
    longo["derrota"] = (longo["pontos"] == 0).astype(int)
    return longo.sort_values(["data", "ID"]).reset_index(drop=True)


def tabela_classificacao(longo: pd.DataFrame, temporada: int) -> pd.DataFrame:
    """Monta a classificação de uma temporada (pontos, vitórias, saldo, gols)."""
    t = longo[longo["temporada"] == temporada]
    tabela = t.groupby("time").agg(
        J=("ID", "count"), V=("vitoria", "sum"), E=("empate", "sum"), D=("derrota", "sum"),
        GP=("gols_pro", "sum"), GC=("gols_contra", "sum"), Pts=("pontos", "sum"),
    )
    tabela["SG"] = tabela["GP"] - tabela["GC"]
    tabela = tabela.sort_values(["Pts", "V", "SG", "GP"], ascending=False)
    tabela.insert(0, "Pos", range(1, len(tabela) + 1))
    return tabela
