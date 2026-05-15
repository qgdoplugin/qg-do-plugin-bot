import os
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID', '1504563977512943777')
GUILD_ID = '1504158988642685089'

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

def buscar_membro_por_email(email):
    url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members/search?query={email}&limit=1'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        members = response.json()
        if members:
            return members[0]['user']['id']
    return None

def atribuir_cargo(user_id, plano):
    role_id = ROLE_IDS[plano]
    url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}'
    requests.put(url, headers=HEADERS)

def remover_cargo(user_id, plano):
    role_id = ROLE_IDS[plano]
    url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}'
    requests.delete(url, headers=HEADERS)

def enviar_embed(nome, email, data_compra, plano, tipo, cargo_atribuido=False):
    url = f'https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages'

    if tipo == 'entrada':
        status_cargo = '✅ Cargo atribuído automaticamente' if cargo_atribuido else '⚠️ Cargo não atribuído — usuário não encontrado no servidor'
        embed = {
            "title": f"{PLAN_EMOJI[plano]} NOVO MEMBRO {plano.upper()}",
            "description": "Um novo assinante acaba de entrar no **QG do Plugin**.",
            "color": PLAN_COLORS[plano],
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de entrada", "value": data_compra, "inline": True},
                {"name": "🎭 Cargo", "value": status_cargo, "inline": False},
            ],
            "footer": {"text": "QG do Plugin • Acesso liberado via Kiwify"},
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        status_cargo = '✅ Cargo removido automaticamente' if cargo_atribuido else '⚠️ Cargo não removido — usuário não encontrado no servidor'
        embed = {
            "title": f"❌ MEMBRO REMOVIDO {plano.upper()}",
            "description": "Um assinante cancelou ou expirou no **QG do Plugin**.",
            "color": 0xFF0000,
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano cancelado", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de saída", "value": data_compra, "inline": True},
                {"name": "🎭 Cargo", "value": status_cargo, "inline": False},
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

    user_id = buscar_membro_por_email(email)
    cargo_atribuido = False

    if event == 'order.approved':
        if user_id:
            atribuir_cargo(user_id, plano)
            cargo_atribuido = True
        enviar_embed(nome, email, data_compra, plano, 'entrada', cargo_atribuido)

    elif event in ['subscription.canceled', 'subscription.expired']:
        if user_id:
            remover_cargo(user_id, plano)
            cargo_atribuido = True
        enviar_embed(nome, email, data_compra, plano, 'saida', cargo_atribuido)

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
