import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# Seu Token gerado no BotFather
TOKEN = "8812668800:AAHhAI9keRnUyPgZ5Ssv-_Swr0WP-ENM6wc"

# Função que apenas pesquisa a música e extrai o link direto e o título (Sem baixar)
def pesquisar_link_musica(nome_musica):
    opcoes_busca = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1', # Busca apenas o primeiro resultado
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(opcoes_busca) as ydl:
        info = ydl.extract_info(nome_musica, download=False) # download=False não gera bloqueio pesado de IP
        if info and 'entries' in info and len(info['entries']) > 0:
            video = info['entries'][0]
            return video['webpage_url'], video['title']
    return None, None

# Função interna acionada pelo clique do botão para realizar o download real
def baixar_audio_por_link(link_direto):
    opcoes_download = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'http_chunk_size': 1048576, # Burlar bloqueio camuflando tráfego
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
        "Agora ficou mais fácil! Envie o nome de uma música.\n"
        "Eu irei identificar o melhor link e te darei um *botão para baixar* de forma segura!"
    )
    await update.message.reply_text(instrucao, parse_mode="Markdown")

# Processador de texto que identifica a música e gera o botão interativo
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome_musica = update.message.text.strip()
    status_busca = await update.message.reply_text(f"🔍 Buscando referências para: '{nome_musica}'...")
    
    url_direta, titulo_video = pesquisar_link_musica(nome_musica)
    await status_busca.delete()
    
    if not url_direta:
        await update.message.reply_text("❌ Não consegui identificar um link estável para essa busca na nuvem.")
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
    await query.answer() # Avisa ao Telegram que o clique foi recebido
    
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
    # Novo gatilho que escuta os cliques nos botões da tela
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



