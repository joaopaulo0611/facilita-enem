"""Camada de inscrições: notas de corte do SISU tratadas para o assistente.

Primeira versão da Fase 2 (ver docs/FASE2_INSCRICOES.md): só o SISU 2024, a
partir do repositório público maiakanegae/sisu-data (licença MIT, dados
coletados das APIs do SISU, sem caráter oficial).

O arquivo de origem (grades.csv) tem uma linha por curso, sem cabeçalho, com
21 campos fixos seguidos de um bloco de 5 campos para cada modalidade:

    código; curso; grau; turno; vagas; campus; município; UF; IES; sigla;
    peso CN; peso CH; peso LC; peso MT; peso redação;
    nota mínima CN; CH; LC; MT; redação; média mínima;
    [modalidade; vagas; nota de corte; bônus %; data da nota de corte] ...

Atenção à ordem dos pesos: Natureza vem antes de Humanas e Linguagens.

Aqui cada bloco vira uma linha (curso × modalidade). O texto longo da modalidade
é mantido e ganha um grupo legível ("Ampla concorrência", "Lei de Cotas: ..." ou
"Ação afirmativa da instituição"). O resultado vai para data/inscricoes/sisu.parquet,
que é pequeno (menos de 1 MB) e versionado, como a Gold.

Os dados são pequenos (12 MB por ano), então o tratamento usa pandas, sem Spark.

Uso:
    python etl/inscricoes.py                # baixa o que faltar, confere e trata
    python etl/inscricoes.py --sem-download # usa só os CSVs já baixados
"""
import argparse
import csv
import hashlib
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
FONTES = Path(__file__).resolve().parent / "fontes_inscricoes.json"
PASTA = RAIZ / "data" / "inscricoes"
BRUTO = PASTA / "bruto"  # CSVs de origem: não versionados (data/inscricoes/* no .gitignore)
SAIDA = PASTA / "sisu.parquet"

ANOS = [2024]
URL = "https://raw.githubusercontent.com/maiakanegae/sisu-data/main/data/{ano}/scraping/grades.csv"

CAMPOS_FIXOS = 21
CAMPOS_MODALIDADE = 5
AREAS = ["cn", "ch", "lc", "mt", "redacao"]  # ordem dos pesos e das notas mínimas no arquivo


def caminho_bruto(ano: int) -> Path:
    return BRUTO / f"sisu_{ano}_grades.csv"


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for pedaco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(pedaco)
    return h.hexdigest()


def garantir_arquivo(ano: int, fontes: dict, baixar: bool) -> Path:
    """Baixa o CSV do ano se faltar e confere o SHA-256 registrado no manifesto."""
    destino = caminho_bruto(ano)
    if not destino.exists():
        if not baixar:
            raise SystemExit(f"[sisu {ano}] {destino.relative_to(RAIZ)} não existe; rode sem --sem-download.")
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f"[sisu {ano}] baixando {URL.format(ano=ano)}")
        urllib.request.urlretrieve(URL.format(ano=ano), destino)  # noqa: S310 (URL fixa)

    registros = fontes["sisu"]["apoio_comunidade"]["sha256_por_arquivo"]
    chave = f"{ano}/scraping/grades.csv"
    sha = sha256_de(destino)
    esperado = registros.get(chave, {}).get("sha256")
    if esperado and esperado != sha:
        raise SystemExit(
            f"[sisu {ano}] SHA-256 diferente do registrado em {FONTES.name}: o arquivo mudou na origem "
            "ou veio corrompido. Confira antes de atualizar o manifesto."
        )
    if not esperado:
        registros[chave] = {"sha256": sha, "bytes": destino.stat().st_size, "url": URL.format(ano=ano)}
        fontes["sisu"]["apoio_comunidade"]["coletado_em"] = date.today().isoformat()
        print(f"[sisu {ano}] registrado em {FONTES.name}: sha256 {sha[:16]}…")
    else:
        print(f"[sisu {ano}] integridade confirmada (sha256 {sha[:16]}…)")
    return destino


def grupo_modalidade(texto: str) -> tuple[str, str]:
    """Classifica a modalidade em (tipo, grupo legível) a partir do texto do SISU."""
    t = texto.lower()
    if t.startswith("ampla concorr"):
        return "ampla", "Ampla concorrência"
    if "12.711" not in t:
        return "cota", "Ação afirmativa da instituição"
    condicoes = ["escola pública"]
    if re.search(r"inferior a 1(,0)? salário", t):
        condicoes.append("renda até 1 SM")
    if "pretos, pardos ou indígenas" in t:
        condicoes.append("pretos, pardos ou indígenas")
    elif "pretos ou pardos" in t:
        condicoes.append("pretos ou pardos")
    elif "indígenas" in t:
        condicoes.append("indígenas")
    if "quilombola" in t:
        condicoes.append("quilombolas")
    if "deficiência" in t:
        condicoes.append("pessoas com deficiência")
    return "cota", "Lei de Cotas: " + ", ".join(condicoes)


def numero(texto: str) -> float | None:
    """Converte um campo numérico do SISU; vazio vira nulo (não zero)."""
    texto = texto.strip()
    return float(texto) if texto else None


def ler_ano(ano: int, arquivo: Path) -> pd.DataFrame:
    """Desdobra cada curso em uma linha por modalidade."""
    linhas = []
    with arquivo.open(encoding="utf-8", newline="") as f:
        for n, campos in enumerate(csv.reader(f, delimiter=";"), start=1):
            if len(campos) < CAMPOS_FIXOS or (len(campos) - CAMPOS_FIXOS) % CAMPOS_MODALIDADE:
                raise ValueError(f"[sisu {ano}] linha {n} com {len(campos)} campos: formato inesperado")
            fixos = campos[:CAMPOS_FIXOS]
            curso = {
                "ano": ano,
                "codigo_curso": int(fixos[0]),
                "curso": " ".join(fixos[1].split()),
                "grau": fixos[2].strip(),
                "turno": fixos[3].strip(),
                "vagas_curso": int(fixos[4] or 0),
                "campus": " ".join(fixos[5].split()),
                "municipio": fixos[6].strip(),
                "uf": fixos[7].strip(),
                "ies_nome": " ".join(fixos[8].split()),
                "ies_sigla": fixos[9].strip(),
                **{f"peso_{a}": numero(v) for a, v in zip(AREAS, fixos[10:15])},
                **{f"nota_min_{a}": numero(v) for a, v in zip(AREAS, fixos[15:20])},
                "media_minima": numero(fixos[20]),
            }
            for i in range(CAMPOS_FIXOS, len(campos), CAMPOS_MODALIDADE):
                texto, vagas, corte, bonus, _data = campos[i : i + CAMPOS_MODALIDADE]
                tipo, grupo = grupo_modalidade(texto)
                linhas.append(
                    {
                        **curso,
                        "modalidade": texto.strip(),
                        "modalidade_tipo": tipo,
                        "modalidade_grupo": grupo,
                        "vagas_modalidade": int(vagas or 0),
                        "nota_corte": numero(corte),  # vazio = modalidade sem nota de corte
                        "bonus_pct": numero(bonus) or 0.0,
                    }
                )
    return pd.DataFrame(linhas)


def compactar(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos pequenos: texto repetido como categoria e números em 32 bits ou menos."""
    for coluna in df.columns:
        if df[coluna].dtype == object:
            df[coluna] = df[coluna].astype("category")
        elif coluna.startswith(("peso_", "nota_", "media_", "bonus_")):
            df[coluna] = df[coluna].astype("float32")
    df["ano"] = df["ano"].astype("int16")
    df["codigo_curso"] = df["codigo_curso"].astype("int32")
    df["vagas_curso"] = df["vagas_curso"].astype("int16")
    df["vagas_modalidade"] = df["vagas_modalidade"].astype("int16")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Trata as notas de corte do SISU para o assistente.")
    parser.add_argument("--sem-download", action="store_true", help="não baixa; usa os CSVs já em data/inscricoes/bruto/")
    args = parser.parse_args()

    fontes = json.loads(FONTES.read_text(encoding="utf-8"))
    partes = [ler_ano(ano, garantir_arquivo(ano, fontes, baixar=not args.sem_download)) for ano in ANOS]
    FONTES.write_text(json.dumps(fontes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    df = compactar(pd.concat(partes, ignore_index=True))
    PASTA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA, compression="zstd", index=False)

    sem_corte = df["nota_corte"].isna().sum()
    print(
        f"[sisu] {df['codigo_curso'].nunique():,} cursos, {len(df):,} linhas curso × modalidade "
        f"({sem_corte:,} sem nota de corte), {df['modalidade_grupo'].nunique()} grupos de modalidade"
    )
    print(f"[sisu] gravado {SAIDA.relative_to(RAIZ)} ({SAIDA.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
