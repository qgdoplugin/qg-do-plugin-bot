import os
from datetime import datetime
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID', '1504563977512943777')

ROLE_IDS = {
    'prata': os.environ.get('ROLE_PRATA', '1504562168866013295'),
    'ouro': os.environ.get('ROLE_OURO', '1504562353503600771'),
    'diamante': os.environ.get('ROLE_DIAMANTE', '1504561945590628352'),
}

PLAN_NAMES = {
    'prata': 'VIP Prata — R$14,99/mes',
    'ouro': 'VIP Ouro — R$29,99/mes',
    'diamante': 'VIP Diamante — R$49,99/mes',
}

PLAN_COLORS = {
    'prata': 0xC0C0C0,
    'ouro': 0xFFD700,
    'diamante': 0x00BFFF,
}

PLAN_EMOJI = {
    'prata': '🩶',
    'ouro': '🥇',
    'diamante': '💎',
}

HEADERS = {
    'Authorization': f'Bot {DISCORD_TOKEN}',
    'Content-Type': 'application/json'
}

def enviar_embed(nome, email, data_compra, plano, tipo):
    url = f'https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages'

    if tipo == 'entrada':
        embed = {
            "title": f"{PLAN_EMOJI[plano]} NOVO MEMBRO {plano.upper()}",
            "description": f"Um novo assinante acaba de entrar no **QG do Plugin**.",
            "color": PLAN_COLORS[plano],
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de entrada", "value": data_compra, "inline": True},
                {"name": "✅ Status", "value": "Acesso liberado", "inline": True},
            ],
            "footer": {"text": "QG do Plugin • Acesso liberado via Kiwify"},
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        embed = {
            "title": f"❌ MEMBRO REMOVIDO {plano.upper()}",
            "description": f"Um assinante cancelou ou expirou no **QG do Plugin**.",
            "color": 0xFF0000,
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano cancelado", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de saída", "value": data_compra, "inline": True},
                {"name": "🚫 Status", "value": "Acesso removido", "inline": True},
            ],
            "footer": {"text": "QG do Plugin • Acesso removido via Kiwify"},
            "timestamp": datetime.utcnow().isoformat()
        }

    payload = {"embeds": [embed]}
    requests.post(url, json=payload, headers=HEADERS)

@app.route('/')
def home():
    return 'Bot do QG do Plugin esta online!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({'error': 'Sem dados'}), 400

    event = data.get('event', '')
    customer = data.get('customer', {})
    product = data.get('product', {})

    nome = customer.get('name', 'Desconhecido')
    email = customer.get('email', 'Desconhecido')
    data_compra = datetime.now().strftime('%d/%m/%Y %H:%M')

    product_name = product.get('name', '').lower()
    plano = None
    for key in ROLE_IDS:
        if key in product_name:
            plano = key
            break

    if not plano:
        return jsonify({'error': 'Plano nao identificado'}), 400

    if event == 'order.approved':
        enviar_embed(nome, email, data_compra, plano, 'entrada')

    elif event in ['subscription.canceled', 'subscription.expired']:
        enviar_embed(nome, email, data_compra, plano, 'saida')

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
