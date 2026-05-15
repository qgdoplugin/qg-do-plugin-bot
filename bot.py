import discord
from discord.ext import commands
from flask import Flask, request, jsonify
import threading
import os
import asyncio
from datetime import datetime

# Configurações
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID', '1504563977512943777'))

ROLE_IDS = {
    'prata': int(os.environ.get('ROLE_PRATA', '1504562168866013295')),
    'ouro': int(os.environ.get('ROLE_OURO', '1504562353503600771')),
    'diamante': int(os.environ.get('ROLE_DIAMANTE', '1504561945590628352')),
}

PLAN_NAMES = {
    'prata': 'VIP Prata — R$14,99/mês',
    'ouro': 'VIP Ouro — R$29,99/mês',
    'diamante': 'VIP Diamante — R$49,99/mês',
}

# Bot do Discord
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Servidor Flask para receber webhooks
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot do QG do Plugin está online!'

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

    # Detecta o plano pelo nome do produto
    product_name = product.get('name', '').lower()
    plano = None
    for key in ROLE_IDS:
        if key in product_name:
            plano = key
            break

    if not plano:
        return jsonify({'error': 'Plano não identificado'}), 400

    if event == 'order.approved':
        asyncio.run_coroutine_threadsafe(
            enviar_log(nome, email, data_compra, plano, 'entrada'),
            bot.loop
        )
    elif event in ['subscription.canceled', 'subscription.expired']:
        asyncio.run_coroutine_threadsafe(
            enviar_log(nome, email, data_compra, plano, 'saida'),
            bot.loop
        )

    return jsonify({'status': 'ok'}), 200

async def enviar_log(nome, email, data_compra, plano, tipo):
    canal = bot.get_channel(LOG_CHANNEL_ID)
    if not canal:
        return

    if tipo == 'entrada':
        mensagem = f"""✅ | NOVO MEMBRO {plano.upper()}

👤 Usuário: {nome}
📧 E-mail: {email}
📅 Data de entrada: {data_compra}
📦 Plano: {PLAN_NAMES[plano]}

Acesso liberado automaticamente via Kiwify."""
    else:
        mensagem = f"""❌ | MEMBRO REMOVIDO {plano.upper()}

👤 Usuário: {nome}
📧 E-mail: {email}
📅 Data de saída: {data_compra}
📦 Plano cancelado: {PLAN_NAMES[plano]}

Acesso removido automaticamente via Kiwify."""

    await canal.send(mensagem)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    bot.run(DISCORD_TOKEN)
