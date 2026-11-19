"""Baixa, verifica e extrai os microdados do ENEM a partir de etl/fontes.json.

Resolve o download manual e pesado do portal do INEP:
- Só baixa o ZIP de um ano se ele ainda não existir (ou se o tamanho não bater).
- Só extrai se o CSV de destino ainda não estiver no lugar que o pipeline espera.
- Registra tamanho e SHA-256 em fontes.json na primeira vez, e nas próximas
  execuções confere o download contra esse valor (a "verificação das planilhas").

Uso:
    python etl/baixar_microdados.py            # todos os anos de fontes.json
    python etl/baixar_microdados.py 2023       # só um ano
    python etl/baixar_microdados.py --verificar # só confere o que já existe, sem baixar

Os ZIPs ficam em public/ e são apagados após a extração por padrão (são pesados
e não são versionados). Use --manter-zip para conservá-los.
"""
import argparse
import hashlib
import json
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = Path(__file__).resolve().parent / "fontes.json"
PUBLIC = RAIZ / "public"

PEDACO = 1024 * 1024  # 1 MiB por leitura, para barra de progresso e baixo uso de memória
TENTATIVAS = 4  # o INEP derruba conexões de forma intermitente; vale repetir

# Um ZIP de microdados do INEP tem centenas de MB. Abaixo deste piso, o que
# "baixou" é quase certamente uma página de erro/redirect disfarçada de ZIP
# (foi o que gerou o BadZipFile: o curl salvou um corpo de ~45 KB com status 200).
MINIMO_ZIP_BYTES = 10 * 1024 * 1024  # 10 MiB
ASSINATURA_ZIP = b"PK\x03\x04"  # todo ZIP começa com esta marca

# O download.inep.gov.br frequentemente recusa clientes que não parecem um
# navegador (devolve ConnectionReset no handshake). Estes cabeçalhos imitam um.
CABECALHOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/zip,application/octet-stream,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Connection": "keep-alive",
}


def carregar_fontes() -> dict:
    return json.loads(FONTES.read_text(encoding="utf-8"))


def salvar_fontes(dados: dict) -> None:
    FONTES.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def csv_destino(ano: str) -> Path:
    """Onde o config.py do pipeline espera encontrar o CSV daquele ano."""
    return PUBLIC / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv"


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(PEDACO), b""):
            h.update(bloco)
    return h.hexdigest()


def motivo_zip_invalido(caminho: Path) -> str | None:
    """Devolve o motivo de o arquivo não ser um ZIP de microdados válido, ou None se estiver ok.

    Protege contra o download "com sucesso" do arquivo errado: o INEP responde a
    alguns clientes com um redirect/HTML curto (status 200), que seria aceito como
    ZIP e só estouraria depois, na extração, com um BadZipFile confuso.
    """
    if not caminho.exists():
        return "arquivo não foi criado"
    tamanho = caminho.stat().st_size
    if tamanho < MINIMO_ZIP_BYTES:
        return (
            f"tem só {tamanho / 1e6:,.2f} MB (mínimo esperado: {MINIMO_ZIP_BYTES / 1e6:,.0f} MB) — "
            "provavelmente uma página de erro/redirect do INEP, não o ZIP"
        )
    with caminho.open("rb") as f:
        if f.read(4) != ASSINATURA_ZIP:
            return "não começa com a assinatura de um ZIP (PK\\x03\\x04)"
    return None


def _abrir(url: str, contexto: ssl.SSLContext | None, desde: int = 0):
    cabecalhos = dict(CABECALHOS)
    if desde:
        cabecalhos["Range"] = f"bytes={desde}-"  # retoma de onde parou
    requisicao = urllib.request.Request(url, headers=cabecalhos)
    return urllib.request.urlopen(requisicao, context=contexto, timeout=120)  # noqa: S310 (URL fixa do INEP)


def _contexto_ssl(verificar: bool) -> ssl.SSLContext:
    contexto = ssl.create_default_context()
    if not verificar:
        # download.inep.gov.br costuma ter cadeia de certificado incompleta.
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
    return contexto


def _baixar_urllib(url: str, parcial: Path) -> bool:
    """Tenta baixar com a biblioteca padrão, com retomada parcial. True se completou."""
    verificar = True
    for tentativa in range(1, TENTATIVAS + 1):
        desde = parcial.stat().st_size if parcial.exists() else 0
        try:
            resposta = _abrir(url, _contexto_ssl(verificar), desde)
        except urllib.error.URLError as erro:
            if isinstance(erro.reason, ssl.SSLCertVerificationError) and verificar:
                print("  aviso: certificado SSL do INEP não pôde ser verificado; seguindo sem verificar.")
                verificar = False
                continue
            print(f"  tentativa {tentativa}/{TENTATIVAS} falhou ({erro.reason}); aguardando…")
            if tentativa == TENTATIVAS:
                return False
            time.sleep(3 * tentativa)
            continue

        # Status 200 recomeça do zero; 206 confirma a retomada do Range.
        modo = "ab" if desde and resposta.status == 206 else "wb"
        baixado = desde if modo == "ab" else 0
        restante = int(resposta.headers.get("Content-Length", 0))
        total = baixado + restante
        try:
            with resposta, parcial.open(modo) as saida:
                while bloco := resposta.read(PEDACO):
                    saida.write(bloco)
                    baixado += len(bloco)
                    alvo = f" / {total / 1e6:,.0f} MB ({100 * baixado / total:.0f}%)" if total else ""
                    print(f"\r  baixando {parcial.stem}: {baixado / 1e6:,.0f} MB{alvo}", end="")
            print()
            return True
        except (urllib.error.URLError, ConnectionResetError, TimeoutError) as erro:
            print(f"\n  conexão interrompida ({erro}); retomando de {parcial.stat().st_size / 1e6:,.0f} MB…")
            if tentativa == TENTATIVAS:
                return False
            time.sleep(3 * tentativa)
    return False


def _baixar_curl(url: str, parcial: Path) -> bool:
    """Fallback: curl costuma passar onde o urllib é barrado. True se completou."""
    curl = shutil.which("curl")
    if not curl:
        return False
    print("  tentando com curl (fallback)…")
    comando = [
        curl, "-L", "--fail", "--retry", "5", "--retry-delay", "3",
        # Trata o redirect como erro em vez de salvar o corpo dele como "arquivo":
        # era o 307 do INEP virando um ZIP de 45 KB e estourando na extração.
        "--max-redirs", "10",
        "-C", "-",  # retoma download parcial
        "-A", CABECALHOS["User-Agent"],
        "-o", str(parcial), url,
    ]
    return subprocess.run(comando).returncode == 0  # noqa: S603 (comando montado internamente)


def baixar(url: str, destino: Path) -> None:
    """Baixa para .parcial e renomeia no fim; grava em disco permitindo retomar.

    O servidor do INEP derruba conexões de forma intermitente e recusa clientes
    que não parecem navegador. Encaramos isso com cabeçalhos de navegador,
    retentativas com retomada parcial e, se nada disso bastar, um fallback para
    o curl do sistema.
    """
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if _baixar_urllib(url, parcial) or _baixar_curl(url, parcial):
        # Um download pode "terminar com sucesso" e ainda ser o arquivo errado
        # (página de erro/redirect do INEP salva como ZIP). Validamos antes de
        # aceitar; a integridade exata é conferida depois pelo SHA-256.
        motivo = motivo_zip_invalido(parcial)
        if motivo:
            baixado = parcial.stat().st_size if parcial.exists() else 0
            parcial.unlink(missing_ok=True)  # não deixa lixo para a próxima execução "reaproveitar"
            raise RuntimeError(
                f"O download de {url} terminou, mas o arquivo é inválido: {motivo}.\n"
                f"(baixou {baixado / 1e6:,.2f} MB)\n"
                "O servidor do INEP devolveu um redirect/erro em vez do ZIP. Alternativas:\n"
                f"  1. Baixe o arquivo pelo navegador a partir do portal do INEP e salve em:\n"
                f"       {destino.parent / (destino.stem + '.zip')}\n"
                "     Depois rode o pipeline de novo (ele reaproveita o ZIP que já está lá).\n"
                "  2. Rode de novo mais tarde (o portal costuma oscilar)."
            )
        parcial.replace(destino)
        return
    raise RuntimeError(
        f"Não foi possível baixar {url}.\n"
        "O servidor do INEP está recusando a conexão. Alternativas:\n"
        f"  1. Baixe o arquivo pelo navegador e salve em: {destino.parent / (destino.stem + '.zip')}\n"
        "  2. Rode de novo mais tarde (o download retoma de onde parou)."
    )


def extrair_csv(zip_path: Path, ano: str) -> Path:
    """Extrai apenas a árvore DADOS/ do ZIP e deixa o CSV no caminho que o pipeline espera.

    O ZIP do INEP traz uma pasta raiz (microdados_enem_AAAA/ ou _novo/); achamos o
    MICRODADOS_ENEM_AAAA.csv onde quer que ele esteja e o movemos para o lugar certo.
    """
    destino = csv_destino(ano)
    destino.parent.mkdir(parents=True, exist_ok=True)
    alvo = f"MICRODADOS_ENEM_{ano}.csv".lower()
    with zipfile.ZipFile(zip_path) as z:
        nome_no_zip = next((n for n in z.namelist() if n.lower().endswith(alvo)), None)
        if nome_no_zip is None:
            raise FileNotFoundError(f"{zip_path.name} não contém MICRODADOS_ENEM_{ano}.csv")
        print(f"  extraindo {nome_no_zip} -> {destino.relative_to(RAIZ)}")
        with z.open(nome_no_zip) as origem, destino.open("wb") as saida:
            shutil.copyfileobj(origem, saida, length=PEDACO)
    return destino


def processar_ano(ano: str, fonte: dict, so_verificar: bool, manter_zip: bool) -> bool:
    """Garante o CSV do ano no lugar. Devolve True se fontes.json foi atualizado."""
    destino = csv_destino(ano)
    esperado_sha = fonte.get("sha256")
    esperado_bytes = fonte.get("bytes")
    zip_path = PUBLIC / f"microdados_enem_{ano}.zip"
    atualizou_fontes = False

    if destino.exists():
        print(f"[{ano}] CSV já presente ({destino.stat().st_size / 1e6:,.0f} MB) em {destino.relative_to(RAIZ)}")
        return False

    if so_verificar:
        print(f"[{ano}] CSV ausente — rode sem --verificar para baixar")
        return False

    # Reaproveita um ZIP já baixado se for válido e o tamanho bater; senão (re)baixa.
    # A validação aqui também descarta um ZIP-lixo deixado por uma execução antiga.
    precisa_baixar = True
    if zip_path.exists():
        motivo = motivo_zip_invalido(zip_path)
        if motivo:
            print(f"[{ano}] ZIP existente é inválido ({motivo}); rebaixando")
            zip_path.unlink(missing_ok=True)
        else:
            tamanho = zip_path.stat().st_size
            if esperado_bytes in (None, tamanho):
                print(f"[{ano}] ZIP já baixado ({tamanho / 1e6:,.0f} MB), reaproveitando")
                precisa_baixar = False
            else:
                print(f"[{ano}] ZIP existente tem tamanho inesperado ({tamanho} != {esperado_bytes}); rebaixando")

    if precisa_baixar:
        print(f"[{ano}] baixando de {fonte['url']}")
        baixar(fonte["url"], zip_path)

    tamanho = zip_path.stat().st_size
    print(f"[{ano}] verificando integridade do ZIP…")
    sha = sha256_de(zip_path)
    if esperado_sha and sha != esperado_sha:
        raise ValueError(
            f"[{ano}] SHA-256 não confere!\n  esperado: {esperado_sha}\n  obtido:   {sha}\n"
            "O arquivo pode estar corrompido ou o INEP republicou os microdados."
        )
    if esperado_sha is None or esperado_bytes is None:
        fonte["sha256"], fonte["bytes"] = sha, tamanho
        atualizou_fontes = True
        print(f"[{ano}] registrado em fontes.json: {tamanho / 1e6:,.0f} MB, sha256 {sha[:16]}…")
    else:
        print(f"[{ano}] integridade confirmada (sha256 {sha[:16]}…)")

    extrair_csv(zip_path, ano)
    # Só apaga o ZIP se foi o script que o baixou. Um ZIP que já estava lá
    # (ex.: baixado à mão pelo navegador) é preservado, para não dar trabalho de novo.
    if precisa_baixar and not manter_zip:
        zip_path.unlink()
        print(f"[{ano}] ZIP removido (use --manter-zip para conservar)")
    print(f"[{ano}] pronto.")
    return atualizou_fontes


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa e verifica os microdados do ENEM (INEP).")
    parser.add_argument("anos", nargs="*", help="anos a processar (padrão: todos os de fontes.json)")
    parser.add_argument("--verificar", action="store_true", help="não baixa; só confere o que já existe")
    parser.add_argument("--manter-zip", action="store_true", help="não apaga o ZIP após extrair")
    args = parser.parse_args()

    fontes = carregar_fontes()
    anos = args.anos or list(fontes["anos"])
    atualizou = False
    for ano in anos:
        if ano not in fontes["anos"]:
            print(f"[{ano}] não está em fontes.json — anos disponíveis: {', '.join(fontes['anos'])}", file=sys.stderr)
            continue
        atualizou |= processar_ano(ano, fontes["anos"][ano], args.verificar, args.manter_zip)
    if atualizou:
        salvar_fontes(fontes)


if __name__ == "__main__":
    main()
