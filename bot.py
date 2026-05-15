import os
from datetime import datetime
from flask import Flask, request, jsonify
import requests

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

HEADERS = {
    'Authorization': f'Bot {DISCORD_TOKEN}',
    'Content-Type': 'application/json'
}

def enviar_mensagem(mensagem):
    url = f'https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages'
    payload = {'content': mensagem}
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
        mensagem = f"""NOVO MEMBRO {plano.upper()}

Usuario: {nome}
E-mail: {email}
Data de entrada: {data_compra}
Plano: {PLAN_NAMES[plano]}

Acesso liberado automaticamente via Kiwify."""
        enviar_mensagem(mensagem)

    elif event in ['subscription.canceled', 'subscription.expired']:
        mensagem = f"""MEMBRO REMOVIDO {plano.upper()}

Usuario: {nome}
E-mail: {email}
Data de saida: {data_compra}
Plano cancelado: {PLAN_NAMES[plano]}

Acesso removido automaticamente via Kiwify."""
        enviar_mensagem(mensagem)

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
