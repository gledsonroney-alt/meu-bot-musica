import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# Seu Token gerado no BotFather
TOKEN = "8812668800:AAHhAI9keRnUyPgZ5Ssv-_Swr0WP-ENM6wc"

# Função que pesquisa a música no SoundCloud para pegar o link (Livre de bloqueio de IP)
def pesquisar_link_musica(nome_musica):
    opcoes_busca = {
        'format': 'bestaudio/best',
        'default_search': 'scsearch1', # Busca o primeiro resultado no SoundCloud
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(opcoes_busca) as ydl:
            info = ydl.extract_info(nome_musica, download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                return video['webpage_url'], video['title']
    except Exception as e:
        print(f"Erro na busca: {str(e)}")
    return None, None

# Função interna que baixa o áudio a partir do link encontrado
def baixar_audio_por_link(link_direto):
    opcoes_download = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(opcoes_download) as ydl:
        info = ydl.extract_info(link_direto, download=True)
        filename = ydl.prepare_filename(info)
        nome_base, _ = os.path.splitext(filename)
        return nome_base + ".mp3"

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instrucao = (
        "🎵 *Bem-vindo ao Buscador Resiliente de Músicas!* 🎵\n\n"
        "Envie o nome de uma música.\n"
        "Eu irei identificar o link e te darei um *botão para baixar* em MP3!"
    )
    await update.message.reply_text(instrucao, parse_mode="Markdown")

# Processador de texto que identifica a música e gera o botão interativo
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome_musica = update.message.text.strip()
    status_busca = await update.message.reply_text(f"🔍 Buscando referências para: '{nome_musica}'...")
    
    url_direta, titulo_video = pesquisar_link_musica(nome_musica)
    await status_busca.delete()
    
    if not url_direta:
        await update.message.reply_text("❌ Não consegui identificar essa música nas plataformas livres na nuvem.")
        return

    # Criação do botão físico integrado na mensagem do Telegram
    teclado = [[InlineKeyboardButton(text="⬇️ Confirmar e Baixar MP3", callback_data=f"dl_link|{url_direta}")]]
    reply_markup = InlineKeyboardMarkup(teclado)
    
    await update.message.reply_text(
        f"📌 *Resultado Encontrado:*\n`{titulo_video}`\n\nClique no botão abaixo para processar o áudio:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Captura e gerencia o clique no botão físico de download
async def escutar_clique_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dados = query.data.split("|")
    if dados[0] == "dl_link":
        link_alvo = dados[1]
        progresso = await query.message.reply_text("⏳ Processando e convertendo arquivo MP3 na nuvem...")
        
        try:
            os.makedirs("downloads", exist_ok=True)
            caminho_arquivo = baixar_audio_por_link(link_alvo)
            
            with open(caminho_arquivo, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=os.path.basename(caminho_arquivo))
                
            os.remove(caminho_arquivo)
            await progresso.delete()
            
        except Exception as e:
            await query.message.reply_text(f"❌ Erro crítico ao processar o link: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).read_timeout(120).write_timeout(120).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
    app.add_handler(CallbackQueryHandler(escutar_clique_botao))
    
    print("Bot com botões interativos rodando...")
    app.run_polling()

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")




