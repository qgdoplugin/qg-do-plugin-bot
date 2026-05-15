import os
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
LOG_CHANNEL_ID = os.environ.get('LOG_CHANNEL_ID', '1504563977512943777')
VERIFY_CHANNEL_ID = '1504972197272223844'
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

# Banco de dados em memória: email -> {plano, nome}
assinantes = {}

def enviar_mensagem(channel_id, conteudo):
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    payload = {'content': conteudo}
    requests.post(url, json=payload, headers=HEADERS)

def atribuir_cargo(user_id, plano):
    role_id = ROLE_IDS[plano]
    url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}'
    requests.put(url, headers=HEADERS)

def remover_cargo(user_id, plano):
    role_id = ROLE_IDS[plano]
    url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}'
    requests.delete(url, headers=HEADERS)

def enviar_embed_log(nome, email, data_compra, plano, tipo):
    url = f'https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages'

    if tipo == 'entrada':
        embed = {
            "title": f"{PLAN_EMOJI[plano]} NOVO MEMBRO {plano.upper()}",
            "description": "Um novo assinante acaba de entrar no **QG do Plugin**.",
            "color": PLAN_COLORS[plano],
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de entrada", "value": data_compra, "inline": True},
                {"name": "✅ Status", "value": "Aguardando verificação no Discord", "inline": False},
            ],
            "footer": {"text": "QG do Plugin • Kiwify"},
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        embed = {
            "title": f"❌ MEMBRO REMOVIDO {plano.upper()}",
            "description": "Um assinante cancelou ou expirou no **QG do Plugin**.",
            "color": 0xFF0000,
            "fields": [
                {"name": "👤 Usuário", "value": nome, "inline": True},
                {"name": "📧 E-mail", "value": email, "inline": True},
                {"name": "📦 Plano cancelado", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data de saída", "value": data_compra, "inline": True},
                {"name": "🚫 Status", "value": "Acesso removido", "inline": False},
            ],
            "footer": {"text": "QG do Plugin • Kiwify"},
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
    email = customer.get('email', 'Desconhecido').lower()
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
        assinantes[email] = {'plano': plano, 'nome': nome}
        enviar_embed_log(nome, email, data_compra, plano, 'entrada')

    elif event in ['subscription.canceled', 'subscription.expired']:
        if email in assinantes:
            del assinantes[email]
        enviar_embed_log(nome, email, data_compra, plano, 'saida')

    return jsonify({'status': 'ok'}), 200

@app.route('/discord/interactions', methods=['POST'])
def interactions():
    data = request.json
    if not data:
        return jsonify({'error': 'Sem dados'}), 400

    return jsonify({'type': 1})

@app.route('/message', methods=['POST'])
def message():
    data = request.json
    if not data:
        return jsonify({'error': 'Sem dados'}), 400

    channel_id = data.get('channel_id')
    content = data.get('content', '')
    user_id = data.get('user_id')
    username = data.get('username', '')

    if channel_id != VERIFY_CHANNEL_ID:
        return jsonify({'status': 'ignored'}), 200

    if not content.startswith('!verificar '):
        return jsonify({'status': 'ignored'}), 200

    email = content.replace('!verificar ', '').strip().lower()

    if email in assinantes:
        info = assinantes[email]
        plano = info['plano']
        atribuir_cargo(user_id, plano)
        enviar_mensagem(
            VERIFY_CHANNEL_ID,
            f"✅ <@{user_id}> Acesso verificado! Cargo **{plano.upper()}** atribuído com sucesso. Bem-vindo ao QG do Plugin! {PLAN_EMOJI[plano]}"
        )
    else:
        enviar_mensagem(
            VERIFY_CHANNEL_ID,
            f"❌ <@{user_id}> E-mail não encontrado. Verifique se usou o mesmo e-mail da sua assinatura na Kiwify."
        )

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
