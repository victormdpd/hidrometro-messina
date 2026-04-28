"""
Envio de alertas por e-mail via SendGrid
"""

import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "dados" / "config.json"

REMETENTE = "victor@mdpd.com.br"
REMETENTE_NOME = "MD Packet Digital"
DESTINATARIOS = [
    "victor.vallenthe@gmail.com",
]
COPIA = [
    "victor@mdpd.com.br",
    "danielns@mdpd.com.br",
]

GATILHOS = [30, 50, 70, 80, 85, 90, 95, 100]


def ja_enviou_alerta(percentual: int) -> bool:
    """Verifica se o alerta para esse % já foi enviado neste ciclo."""
    alertas_file = ROOT / "dados" / "alertas_enviados.json"
    if not alertas_file.exists():
        return False
    with open(alertas_file, "r") as f:
        alertas = json.load(f)
    config = json.load(open(CONFIG_FILE))
    ciclo = config["data_leitura_inicial"]
    return alertas.get(ciclo, {}).get(str(percentual), False)


def registrar_alerta(percentual: int):
    """Registra que o alerta foi enviado para este % neste ciclo."""
    alertas_file = ROOT / "dados" / "alertas_enviados.json"
    config = json.load(open(CONFIG_FILE))
    ciclo = config["data_leitura_inicial"]

    alertas = {}
    if alertas_file.exists():
        with open(alertas_file, "r") as f:
            alertas = json.load(f)

    if ciclo not in alertas:
        alertas[ciclo] = {}
    alertas[ciclo][str(percentual)] = True

    with open(alertas_file, "w") as f:
        json.dump(alertas, f, indent=2)


def enviar_email(percentual: float, dados: dict):
    """Envia e-mail de alerta via SendGrid."""
    import urllib.request

    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("SENDGRID_API_KEY não encontrada!")
        return False

    config = json.load(open(CONFIG_FILE))

    # Monta o corpo do e-mail
    cor = "#e53e3e" if percentual >= 100 else "#d69e2e" if percentual >= 80 else "#2b6cb0"
    status = "🚨 MÍNIMO ULTRAPASSADO" if percentual >= 100 else "⚠️ ATENÇÃO" if percentual >= 80 else "📊 INFORMATIVO"

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background: #f0f4f8; padding: 2rem; margin: 0;">
      <div style="max-width: 580px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        
        <div style="background: #0a0a0a; padding: 1.5rem 2rem;">
          <p style="color: #a3e635; font-size: 18px; font-weight: bold; margin: 0;">MD PACKET DIGITAL</p>
          <p style="color: #666; font-size: 12px; margin: 4px 0 0;">Monitoramento Inteligente</p>
        </div>

        <div style="padding: 2rem;">
          <div style="background: {cor}15; border-left: 4px solid {cor}; padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1.5rem;">
            <p style="color: {cor}; font-weight: bold; margin: 0; font-size: 15px;">{status}</p>
            <p style="color: {cor}; margin: 4px 0 0; font-size: 13px;">Consumo atingiu <strong>{percentual}%</strong> do mínimo contratado</p>
          </div>

          <h2 style="color: #1a202c; font-size: 16px; margin: 0 0 1rem;">Messina — Hidrômetro</h2>

          <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr style="background: #f7f9fc;">
              <td style="padding: 10px 12px; color: #718096; border-radius: 6px 0 0 6px;">Consumo no ciclo</td>
              <td style="padding: 10px 12px; font-weight: 600; color: #1a202c; text-align: right;">{str(dados['consumo_ciclo_m3']).replace('.', ',')} m³</td>
            </tr>
            <tr>
              <td style="padding: 10px 12px; color: #718096;">Mínimo do ciclo</td>
              <td style="padding: 10px 12px; font-weight: 600; color: #1a202c; text-align: right;">{str(dados['consumo_minimo_m3']).replace('.', ',')} m³</td>
            </tr>
            <tr style="background: #f7f9fc;">
              <td style="padding: 10px 12px; color: #718096;">% do mínimo</td>
              <td style="padding: 10px 12px; font-weight: 600; color: {cor}; text-align: right;">{percentual}%</td>
            </tr>
            <tr>
              <td style="padding: 10px 12px; color: #718096;">Dias restantes</td>
              <td style="padding: 10px 12px; font-weight: 600; color: #1a202c; text-align: right;">{dados['dias_restantes']} dias</td>
            </tr>
            <tr style="background: #f7f9fc;">
              <td style="padding: 10px 12px; color: #718096;">Custo estimado atual</td>
              <td style="padding: 10px 12px; font-weight: 600; color: #1a202c; text-align: right;">R$ {'{:,.2f}'.format(float(dados['custo_atual_reais'])).replace(',', 'X').replace('.', ',').replace('X', '.')}</td>
            </tr>
            <tr>
              <td style="padding: 10px 12px; color: #718096;">Custo projetado</td>
              <td style="padding: 10px 12px; font-weight: 600; color: {cor}; text-align: right;">R$ {'{:,.2f}'.format(float(dados['custo_projecao_reais'])).replace(',', 'X').replace('.', ',').replace('X', '.')}</td>
            </tr>
          </table>

          <div style="margin-top: 1.5rem; text-align: center;">
            <a href="https://victormdpd.github.io/hidrometro-messina/" 
               style="background: #1a202c; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 500;">
              Ver dashboard completo →
            </a>
          </div>
        </div>

        <div style="background: #f7f9fc; padding: 1rem 2rem; text-align: center; border-top: 1px solid #e2e8f0;">
          <p style="color: #a0aec0; font-size: 11px; margin: 0;">Valores estimados de água + esgoto, sem taxas, juros e multas · MD Packet Digital</p>
        </div>
      </div>
    </body>
    </html>
    """

    assunto = f"[Hidrômetro Messina] Consumo em {percentual}% do mínimo — {dados['dias_restantes']} dias restantes"

    to_list = [{"email": e} for e in DESTINATARIOS]
    cc_list = [{"email": e} for e in COPIA]

    payload = json.dumps({
        "personalizations": [{
            "to": to_list,
            "cc": cc_list,
            "subject": assunto
        }],
        "from": {"email": REMETENTE, "name": REMETENTE_NOME},
        "content": [{"type": "text/html", "value": html}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ E-mail enviado para {DESTINATARIOS} | Status: {resp.status}")
            return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False


def verificar_e_enviar(dados: dict):
    """Verifica se algum gatilho foi atingido e envia o alerta."""
    percentual = float(dados.get("percentual_minimo", 0))

    for gatilho in sorted(GATILHOS):
        if percentual >= gatilho and not ja_enviou_alerta(gatilho):
            print(f"🔔 Gatilho {gatilho}% atingido! Enviando alerta...")
            sucesso = enviar_email(gatilho, dados)
            if sucesso:
                registrar_alerta(gatilho)
            break  # envia um alerta por vez


if __name__ == "__main__":
    # Teste local
    dados_teste = {
        "consumo_ciclo_m3": 1500,
        "consumo_minimo_m3": 2160,
        "percentual_minimo": 69.4,
        "dias_restantes": 15,
        "custo_atual_reais": 27982.08,
        "custo_projecao_reais": 35000.00,
    }
    verificar_e_enviar(dados_teste)
