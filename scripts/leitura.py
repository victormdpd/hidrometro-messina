"""
Leitura Automática de Hidrômetro - Messina Automação
Roda todo dia às 8h via GitHub Actions
"""

import asyncio
import csv
import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from playwright.async_api import async_playwright

# ── Caminhos ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "dados" / "config.json"
CSV_FILE = ROOT / "dados" / "historico.csv"
LOG_FILE = ROOT / "dados" / "log.txt"

# ── Configurações padrão (usadas se config.json não existir)
CONFIG_PADRAO = {
    "leitura_inicial_m3": 4805.1,
    "data_leitura_inicial": "2025-03-18",
    "data_proxima_leitura": "2025-04-18",
    "consumo_minimo_m3": 2160.0,
    "url": "https://monitoramento.mdpd.com.br/main/supervisory/dashboard/ThNkAJvagP"
}

MAX_TENTATIVAS = 4
INTERVALO_RETRY_MINUTOS = 15


def log(msg: str):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha = f"[{timestamp}] {msg}"
    print(linha)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def carregar_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return CONFIG_PADRAO


async def capturar_leitura(url: str) -> float:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)

        try:
            await page.wait_for_selector("text=m3", timeout=15000)
        except Exception:
            pass

        await asyncio.sleep(4)
        conteudo = await page.content()
        await browser.close()

    padroes = [
        r'(\d{1,6}[.,]\d{1,3})\s*(?:m3|m³)',
        r'(\d{3,6})\s*(?:m3|m³)',
    ]
    for padrao in padroes:
        matches = re.findall(padrao, conteudo, re.IGNORECASE)
        if matches:
            return float(matches[0].replace(',', '.'))

    raise ValueError("Valor do hidrômetro não encontrado na página.")


async def capturar_com_retry(url: str) -> float:
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            log(f"Tentativa {tentativa}/{MAX_TENTATIVAS}...")
            valor = await capturar_leitura(url)
            log(f"Leitura capturada: {valor} m³")
            return valor
        except Exception as e:
            log(f"Erro na tentativa {tentativa}: {e}")
            if tentativa < MAX_TENTATIVAS:
                log(f"Aguardando {INTERVALO_RETRY_MINUTOS} minutos...")
                await asyncio.sleep(INTERVALO_RETRY_MINUTOS * 60)

    raise RuntimeError(f"Falha após {MAX_TENTATIVAS} tentativas.")


def calcular_dados(valor_atual: float, config: dict) -> dict:
    hoje = date.today()
    data_inicial = date.fromisoformat(config["data_leitura_inicial"])
    data_proxima = date.fromisoformat(config["data_proxima_leitura"])
    minimo = config["consumo_minimo_m3"]
    leitura_inicial = config["leitura_inicial_m3"]

    dias_total = (data_proxima - data_inicial).days
    dias_decorridos = (hoje - data_inicial).days
    dias_restantes = max((data_proxima - hoje).days, 0)

    consumo = round(valor_atual - leitura_inicial, 2)
    percentual = round((consumo / minimo) * 100, 1)

    media_diaria = round(consumo / dias_decorridos, 2) if dias_decorridos > 0 else 0
    projecao = round(media_diaria * dias_total, 2) if dias_decorridos > 0 else 0
    percentual_projecao = round((projecao / minimo) * 100, 1)

    return {
        "data": hoje.strftime("%d/%m/%Y"),
        "hora": datetime.now().strftime("%H:%M"),
        "valor_atual_m3": valor_atual,
        "consumo_ciclo_m3": consumo,
        "percentual_minimo": percentual,
        "dias_decorridos": dias_decorridos,
        "dias_restantes": dias_restantes,
        "dias_total": dias_total,
        "media_diaria_m3": media_diaria,
        "projecao_m3": projecao,
        "percentual_projecao": percentual_projecao,
        "consumo_minimo_m3": minimo,
        "leitura_inicial_m3": leitura_inicial,
        "data_leitura_inicial": config["data_leitura_inicial"],
        "data_proxima_leitura": config["data_proxima_leitura"],
        "ultrapassou_minimo": consumo >= minimo,
        "status": "leitura_ok"
    }


def salvar_csv(dados: dict):
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

    campos = [
        "data", "hora", "valor_atual_m3", "consumo_ciclo_m3",
        "percentual_minimo", "dias_decorridos", "dias_restantes",
        "dias_total", "media_diaria_m3", "projecao_m3",
        "percentual_projecao", "consumo_minimo_m3", "leitura_inicial_m3",
        "data_leitura_inicial", "data_proxima_leitura",
        "ultrapassou_minimo", "status"
    ]

    linhas = []
    if CSV_FILE.exists():
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("data") != dados["data"]:
                    linhas.append(row)

    linhas.append(dados)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)

    log(f"Salvo em: {CSV_FILE}")


def salvar_falha():
    dados = {
        "data": date.today().strftime("%d/%m/%Y"),
        "hora": datetime.now().strftime("%H:%M"),
        "valor_atual_m3": "",
        "consumo_ciclo_m3": "",
        "percentual_minimo": "",
        "dias_decorridos": "",
        "dias_restantes": "",
        "dias_total": "",
        "media_diaria_m3": "",
        "projecao_m3": "",
        "percentual_projecao": "",
        "consumo_minimo_m3": "",
        "leitura_inicial_m3": "",
        "data_leitura_inicial": "",
        "data_proxima_leitura": "",
        "ultrapassou_minimo": "",
        "status": "falha_leitura"
    }
    salvar_csv(dados)


async def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log("=" * 50)
    log("Iniciando leitura automática do hidrômetro")

    config = carregar_config()
    log(f"Ciclo: {config['data_leitura_inicial']} → {config['data_proxima_leitura']}")

    try:
        valor = await capturar_com_retry(config["url"])
        dados = calcular_dados(valor, config)
        salvar_csv(dados)

        log(f"Consumo no ciclo: {dados['consumo_ciclo_m3']} m³")
        log(f"% do mínimo: {dados['percentual_minimo']}%")
        log(f"Projeção: {dados['projecao_m3']} m³ ({dados['percentual_projecao']}%)")
        if dados["ultrapassou_minimo"]:
            log("⚠️  ATENÇÃO: Consumo mínimo ultrapassado!")

    except Exception as e:
        log(f"FALHA TOTAL: {e}")
        salvar_falha()

    log("Leitura concluída")
    log("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
