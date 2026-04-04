"""
Leitura Automática de Hidrômetro - Messina Automação
Busca dados direto da API pública - sem navegador
"""

import csv
import json
import time
import requests
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "dados" / "config.json"
CSV_FILE = ROOT / "dados" / "historico.csv"
LOG_FILE = ROOT / "dados" / "log.txt"

API_URL = "https://backend.metam.com.br/api/supervisory/public/ThNkAJvagP?timezone=America%2FSao_Paulo"

CONFIG_PADRAO = {
    "leitura_inicial_m3": 4805.1,
    "data_leitura_inicial": "2026-03-18",
    "data_proxima_leitura": "2026-04-18",
    "consumo_minimo_m3": 2160.0,
    "tarifa_minimo": 7.4143,
    "tarifa_excedente": 16.3115
}

MAX_TENTATIVAS = 4
INTERVALO_RETRY_SEGUNDOS = 60


def log(msg):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha = f"[{timestamp}] {msg}"
    print(linha)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def carregar_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "tarifa_minimo" not in cfg:
            cfg["tarifa_minimo"] = 7.4143
        if "tarifa_excedente" not in cfg:
            cfg["tarifa_excedente"] = 16.3115
        return cfg
    return CONFIG_PADRAO


def capturar_leitura():
    resp = requests.get(API_URL, timeout=15)
    resp.raise_for_status()
    dados = resp.json()
    return float(dados["widgets"][0]["data"]["value"])


def capturar_com_retry():
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            log(f"Tentativa {tentativa}/{MAX_TENTATIVAS}...")
            valor = capturar_leitura()
            log(f"Leitura capturada: {valor} m3")
            return valor
        except Exception as e:
            log(f"Erro na tentativa {tentativa}: {e}")
            if tentativa < MAX_TENTATIVAS:
                log(f"Aguardando {INTERVALO_RETRY_SEGUNDOS}s...")
                time.sleep(INTERVALO_RETRY_SEGUNDOS)
    raise RuntimeError(f"Falha apos {MAX_TENTATIVAS} tentativas.")


def calcular_custo(consumo_m3, minimo, tarifa_minimo, tarifa_excedente):
    custo_minimo = minimo * tarifa_minimo * 2
    if consumo_m3 <= minimo:
        return round(custo_minimo, 2)
    excedente = consumo_m3 - minimo
    return round(custo_minimo + (excedente * tarifa_excedente * 2), 2)


def calcular_dados(valor_atual, config):
    hoje = date.today()
    data_inicial = date.fromisoformat(config["data_leitura_inicial"])
    data_proxima = date.fromisoformat(config["data_proxima_leitura"])
    minimo = config["consumo_minimo_m3"]
    leitura_inicial = config["leitura_inicial_m3"]
    tarifa_minimo = config["tarifa_minimo"]
    tarifa_excedente = config["tarifa_excedente"]

    dias_total = (data_proxima - data_inicial).days
    dias_decorridos = (hoje - data_inicial).days
    dias_restantes = max((data_proxima - hoje).days, 0)

    consumo = round(valor_atual - leitura_inicial, 2)
    percentual = round((consumo / minimo) * 100, 1)
    media_diaria = round(consumo / dias_decorridos, 2) if dias_decorridos > 0 else 0
    projecao = round(media_diaria * dias_total, 2)
    percentual_projecao = round((projecao / minimo) * 100, 1)

    custo_atual = calcular_custo(consumo, minimo, tarifa_minimo, tarifa_excedente)
    custo_projecao = calcular_custo(projecao, minimo, tarifa_minimo, tarifa_excedente)

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
        "custo_atual_reais": custo_atual,
        "custo_projecao_reais": custo_projecao,
        "consumo_minimo_m3": minimo,
        "leitura_inicial_m3": leitura_inicial,
        "data_leitura_inicial": config["data_leitura_inicial"],
        "data_proxima_leitura": config["data_proxima_leitura"],
        "ultrapassou_minimo": consumo >= minimo,
        "status": "leitura_ok"
    }


def salvar_csv(dados):
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "data", "hora", "valor_atual_m3", "consumo_ciclo_m3",
        "percentual_minimo", "dias_decorridos", "dias_restantes",
        "dias_total", "media_diaria_m3", "projecao_m3",
        "percentual_projecao", "custo_atual_reais", "custo_projecao_reais",
        "consumo_minimo_m3", "leitura_inicial_m3",
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
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(linhas)
    log(f"Salvo em: {CSV_FILE}")


def salvar_falha():
    campos = [
        "data", "hora", "valor_atual_m3", "consumo_ciclo_m3",
        "percentual_minimo", "dias_decorridos", "dias_restantes",
        "dias_total", "media_diaria_m3", "projecao_m3",
        "percentual_projecao", "custo_atual_reais", "custo_projecao_reais",
        "consumo_minimo_m3", "leitura_inicial_m3",
        "data_leitura_inicial", "data_proxima_leitura",
        "ultrapassou_minimo", "status"
    ]
    dados = {k: "" for k in campos}
    dados["data"] = date.today().strftime("%d/%m/%Y")
    dados["hora"] = datetime.now().strftime("%H:%M")
    dados["status"] = "falha_leitura"
    salvar_csv(dados)


def main():
    log("=" * 50)
    log("Iniciando leitura automatica do hidrometro")
    config = carregar_config()
    log(f"Ciclo: {config['data_leitura_inicial']} -> {config['data_proxima_leitura']}")
    try:
        valor = capturar_com_retry()
        dados = calcular_dados(valor, config)
        salvar_csv(dados)
        log(f"Consumo no ciclo: {dados['consumo_ciclo_m3']} m3")
        log(f"% do minimo: {dados['percentual_minimo']}%")
        log(f"Custo atual: R$ {dados['custo_atual_reais']}")
        log(f"Custo projecao: R$ {dados['custo_projecao_reais']}")
        if dados["ultrapassou_minimo"]:
            log("ATENCAO: Consumo minimo ultrapassado!")
    except Exception as e:
        log(f"FALHA TOTAL: {e}")
        salvar_falha()
    log("Leitura concluida")
    log("=" * 50)


if __name__ == "__main__":
    main()
