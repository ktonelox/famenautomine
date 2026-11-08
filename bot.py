import discord
from discord.ext import commands
from discord import app_commands
import os
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
AUTH_CHANNEL_ID = 1569080867861696682  # ID канала для авторизации
GUILD_ID = 1569067101493403678        # ID твоего сервера (для быстрой синхронизации)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'[DISCORD] Бот {bot.user} запущен!')
    try:
        # Синхронизируем команды только для твоего сервера (чтобы они появились сразу)
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Синхронизировано {len(synced)} слэш-команд для сервера {GUILD_ID}")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

@bot.tree.command(name="register", description="Авторизовать HWID в AutoMine", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(hwid="Ваш HWID (отображается в окне авторизации в игре)")
async def register(interaction: discord.Interaction, hwid: str):
    # Проверяем, что команда введена в нужном канале
    if interaction.channel_id != AUTH_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Используйте эту команду только в канале <#{AUTH_CHANNEL_ID}>.", ephemeral=True)
        return

    discord_id = str(interaction.user.id)
    
    # Откладываем ответ, чтобы Discord не выдал ошибку таймаута (3 секунды)
    await interaction.response.defer(ephemeral=True)

    try:
        # Записываем в базу
        supabase.table('users').insert({"hwid": hwid, "discord_id": discord_id}).execute()
        
        # Отправляем ЛС
        try:
            await interaction.user.send(f"✅ Вы успешно авторизованы!\nВаш HWID: `{hwid}`\nПерезайдите в Minecraft.")
            await interaction.followup.send(f"✅ Успешно! Проверьте ЛС.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"✅ Вы авторизованы, но я не могу отправить ЛС (закрыты личные сообщения).", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: возможно, этот HWID уже зарегистрирован.", ephemeral=True)
        print(f"Ошибка вставки в БД: {e}")

# --- ВЕБ-СЕРВЕР ДЛЯ KOYEB (чтобы сервис не засыпал) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[KOYEB] Health check server listening on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-сервер в фоне
    Thread(target=run_health_server, daemon=True).start()
    # Запускаем бота
    bot.run(TOKEN)