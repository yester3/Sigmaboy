# main.py - Bot para unir cuentas a servidores

import discord
from discord.ext import commands
import aiohttp
import os
import re
from datetime import datetime

# Tokens del bot principal (para comandos) y cuentas de usuario
BOT_TOKEN = os.getenv('DISCORD_TOKEN')

# Tokens de cuentas de usuario (3 por ahora)
USER_TOKENS = [
    os.getenv('DISCORD_TOKEN1'),
    os.getenv('DISCORD_TOKEN2'),
    os.getenv('DISCORD_TOKEN3'),
]

# Filtrar tokens vacíos
USER_TOKENS = [t for t in USER_TOKENS if t]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=",", intents=intents, help_command=None)

def extract_invite_code(invite_input):
    """Extrae el código de invitación de una URL o código directo"""
    # Si es una URL completa
    patterns = [
        r'(?:discord\.gg|discord\.com/invite)/([a-zA-Z0-9-]+)',
        r'^([a-zA-Z0-9-]+)$'  # Código directo
    ]
    
    for pattern in patterns:
        match = re.search(pattern, invite_input)
        if match:
            return match.group(1)
    
    return None

async def join_server_with_token(token, invite_code):
    """Une una cuenta al servidor usando el token proporcionado"""
    url = f"https://discord.com/api/v9/invites/{invite_code}"
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1NTg4OSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
    }
    
    payload = {}  # POST vacío para aceptar invitación
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                data = await response.json() if response.content else {}
                
                if response.status == 200:
                    # Éxito - se unió al servidor
                    guild_name = data.get('guild', {}).get('name', 'Servidor desconocido')
                    return True, f"Unido a: {guild_name}", None
                    
                elif response.status == 401:
                    return False, "Token inválido o expirado", "invalid_token"
                    
                elif response.status == 403:
                    error_msg = data.get('message', 'Acceso denegado')
                    return False, error_msg, "forbidden"
                    
                elif response.status == 404:
                    return False, "Invitación inválida o expirada", "invalid_invite"
                    
                elif response.status == 429:
                    retry_after = data.get('retry_after', 'desconocido')
                    return False, f"Rate limit - esperar {retry_after}s", "rate_limited"
                    
                else:
                    return False, f"Error {response.status}: {data.get('message', 'Desconocido')}", "error"
                    
        except Exception as e:
            return False, f"Excepción: {str(e)}", "exception"

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print(f'📊 Tokens de usuario cargados: {len(USER_TOKENS)}')
    if not USER_TOKENS:
        print('⚠️ ADVERTENCIA: No se encontraron tokens de usuario en las variables de entorno')

@bot.command()
async def join(ctx, invite: str = None):
    """
    Une las cuentas configuradas a un servidor de Discord.
    Uso: ,join https://discord.gg/CODIGO  o  ,join CODIGO
    """
    if not invite:
        await ctx.send("❌ **Uso:** `,join <invitación>`\nEjemplo: `,join https://discord.gg/abc123` o `,join abc123`")
        return
    
    if not USER_TOKENS:
        await ctx.send("❌ **Error:** No hay tokens de usuario configurados.\nConfigura `DISCORD_TOKEN1`, `DISCORD_TOKEN2` y `DISCORD_TOKEN3` en las variables de entorno.")
        return
    
    # Extraer código de invitación
    invite_code = extract_invite_code(invite)
    if not invite_code:
        await ctx.send("❌ **Error:** Invitación inválida. Usa una URL de Discord o el código directo.")
        return
    
    # Mensaje de progreso
    progress_msg = await ctx.send(f"🔄 **Uniendo cuentas al servidor...**\nCódigo: `{invite_code}`\nTokens: {len(USER_TOKENS)}")
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, token in enumerate(USER_TOKENS, 1):
        success, message, error_type = await join_server_with_token(token, invite_code)
        
        if success:
            results.append(f"✅ **Cuenta {i}:** {message}")
            success_count += 1
        else:
            results.append(f"❌ **Cuenta {i}:** {message}")
            failed_count += 1
        
        # Pequeña pausa entre requests para no saturar
        if i < len(USER_TOKENS):
            await asyncio.sleep(0.5)
    
    # Crear embed de resultados
    embed = discord.Embed(
        title="📊 Resultados de Unión",
        description=f"Invitación: `{invite_code}`",
        color=discord.Color.green() if success_count > 0 else discord.Color.red(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="✅ Exitosos", value=str(success_count), inline=True)
    embed.add_field(name="❌ Fallidos", value=str(failed_count), inline=True)
    embed.add_field(name="📈 Total", value=str(len(USER_TOKENS)), inline=True)
    
    # Agregar detalles de cada cuenta
    details = "\n".join(results)
    if len(details) > 1024:
        details = details[:1021] + "..."
    
    embed.add_field(name="Detalles", value=details, inline=False)
    
    await progress_msg.edit(content=None, embed=embed)

@bot.command()
async def tokens(ctx):
    """Muestra cuántos tokens de usuario están configurados"""
    embed = discord.Embed(
        title="🔑 Configuración de Tokens",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Tokens configurados", value=str(len(USER_TOKENS)), inline=True)
    embed.add_field(name="Variables requeridas", value="DISCORD_TOKEN1\nDISCORD_TOKEN2\nDISCORD_TOKEN3", inline=False)
    
    status = "✅ Listo" if len(USER_TOKENS) == 3 else f"⚠️ Faltan {3 - len(USER_TOKENS)} tokens"
    embed.add_field(name="Estado", value=status, inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def testinvite(ctx, invite: str = None):
    """Verifica si una invitación es válida sin unirse"""
    if not invite:
        await ctx.send("❌ Usa: `,testinvite <código>`")
        return
    
    invite_code = extract_invite_code(invite)
    if not invite_code:
        await ctx.send("❌ Invitación inválida")
        return
    
    # Usar el primer token para verificar
    if not USER_TOKENS:
        await ctx.send("❌ No hay tokens configurados")
        return
    
    url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true&with_expiration=true"
    
    headers = {
        "Authorization": USER_TOKENS[0],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                guild = data.get('guild', {})
                invite_data = data.get('invite', {})
                
                embed = discord.Embed(
                    title="✅ Invitación Válida",
                    color=discord.Color.green()
                )
                embed.add_field(name="Servidor", value=guild.get('name', 'Desconocido'), inline=False)
                embed.add_field(name="Miembros", value=str(data.get('approximate_member_count', '?')), inline=True)
                embed.add_field(name="En línea", value=str(data.get('approximate_presence_count', '?')), inline=True)
                embed.add_field(name="Expira", value="Sí" if data.get('expires_at') else "No", inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Invitación inválida o expirada (Status: {response.status})")

@bot.command()
async def help(ctx):
    """Muestra la ayuda del bot"""
    embed = discord.Embed(
        title="🤖 Comandos Disponibles",
        description="Bot de unión a servidores con múltiples cuentas",
        color=discord.Color.blue()
    )
    
    embed.add_field(name=",join <invitación>", value="Une todas las cuentas al servidor\nEj: `,join discord.gg/abc123`", inline=False)
    embed.add_field(name=",tokens", value="Muestra el estado de los tokens configurados", inline=False)
    embed.add_field(name=",testinvite <invitación>", value="Verifica si una invitación es válida", inline=False)
    embed.add_field(name=",help", value="Muestra este mensaje", inline=False)
    
    embed.add_field(
        name="⚙️ Configuración",
        value="Configura estas variables de entorno:\n• `DISCORD_TOKEN` - Token del bot\n• `DISCORD_TOKEN1` - Token cuenta 1\n• `DISCORD_TOKEN2` - Token cuenta 2\n• `DISCORD_TOKEN3` - Token cuenta 3",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Import necesario para sleep
import asyncio

bot.run(BOT_TOKEN)
