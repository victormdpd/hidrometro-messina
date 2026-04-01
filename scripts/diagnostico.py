"""
Script de diagnóstico - captura screenshot e HTML do site do hidrômetro
"""

import asyncio
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://monitoramento.mdpd.com.br/main/supervisory/dashboard/ThNkAJvagP"
ROOT = Path(__file__).parent.parent


async def diagnostico():
    print("Iniciando diagnóstico...")
    print(f"URL: {URL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        print("Acessando a página...")
        try:
            await page.goto(URL, timeout=30000, wait_until="networkidle")
        except Exception as e:
            print(f"Timeout/erro no goto: {e}")
            print("Tentando continuar mesmo assim...")

        print("Aguardando 8 segundos para carregar...")
        await asyncio.sleep(8)

        # Salva screenshot
        screenshot_path = ROOT / "dados" / "screenshot.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot salvo: {screenshot_path}")

        # Salva HTML
        html = await page.content()
        html_path = ROOT / "dados" / "pagina.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML salvo ({len(html)} chars): {html_path}")

        # Tenta extrair o valor
        print("\n--- Buscando valor do hidrômetro ---")
        padroes = [
            r'(\d{1,6}[.,]\d{1,3})\s*(?:m3|m³)',
            r'(\d{3,6})\s*(?:m3|m³)',
            r'"value"\s*:\s*"?(\d+[.,]?\d*)"?',
            r'(\d{4,6}[.,]\d{0,3})',
        ]
        for padrao in padroes:
            matches = re.findall(padrao, html, re.IGNORECASE)
            if matches:
                print(f"Padrão '{padrao}': {matches[:5]}")

        # Mostra texto visível da página
        texto = await page.evaluate("() => document.body.innerText")
        print(f"\n--- Texto visível na página ---")
        print(texto[:2000] if texto else "(vazio)")

        await browser.close()

    print("\nDiagnóstico concluído!")


if __name__ == "__main__":
    asyncio.run(diagnostico())
