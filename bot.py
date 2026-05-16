import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime
from flask import Flask, request, jsonify
import requests
import threading

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

assinantes = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

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
    requests.post(url, json={"embeds": [embed]}, headers=HEADERS)

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

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command(name='verificar')
async def verificar_cmd(ctx, email: str = None):
    if str(ctx.channel.id) != VERIFY_CHANNEL_ID:
        return

    try:
        await ctx.message.delete()
    except:
        pass

    if not email:
        await ctx.send(f'❌ <@{ctx.author.id}> Use: `!verificar seuemail@email.com`', delete_after=10)
        return

    email = email.lower()
    user_id = str(ctx.author.id)

    if email in assinantes:
        info = assinantes[email]
        plano = info['plano']
        role_id = ROLE_IDS[plano]

        guild = bot.get_guild(int(GUILD_ID))
        member = guild.get_member(int(user_id))
        role = guild.get_role(int(role_id))

        if member and role:
            await member.add_roles(role)

        await ctx.send(
            f'✅ <@{user_id}> Acesso verificado! Cargo **{plano.upper()}** atribuído. Bem-vindo ao QG do Plugin! {PLAN_EMOJI[plano]}',
            delete_after=15
        )

        url = f'https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages'
        embed = {
            "title": "✅ VERIFICAÇÃO CONCLUÍDA",
            "color": PLAN_COLORS[plano],
            "fields": [
                {"name": "👤 Usuário", "value": f'<@{user_id}>', "inline": True},
                {"name": "📦 Plano", "value": PLAN_NAMES[plano], "inline": True},
                {"name": "📅 Data", "value": datetime.now().strftime('%d/%m/%Y %H:%M'), "inline": True},
            ],
            "footer": {"text": "QG do Plugin • Verificação"},
            "timestamp": datetime.utcnow().isoformat()
        }
        requests.post(url, json={"embeds": [embed]}, headers=HEADERS)
    else:
        await ctx.send(
            f'❌ <@{user_id}> E-mail não encontrado. Verifique se usou o mesmo e-mail da assinatura na Kiwify.',
            delete_after=15
        )

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    bot.run(DISCORD_TOKEN)
