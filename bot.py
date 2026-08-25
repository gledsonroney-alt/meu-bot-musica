import os
import asyncio
import re
import urllib.request
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Seu Token gerado no BotFather
TOKEN = "8812668800:AAHhAI9keRnUyPgZ5Ssv-_Swr0WP-ENM6wc"

# Função inteligente que pesquisa o link usando múltiplos motores web abertos
def pesquisar_link_na_web(nome_musica):
    busca_termo = f"{nome_musica} youtube"
    
    # --- IF 1: Tentativa Principal via DuckDuckGo ---
    try:
        print(f"Buscando link na web via DuckDuckGo para: {nome_musica}")
        url_busca = "https://duckduckgo.com" + urllib.parse.quote(busca_termo)
        requisicao = urllib.request.Request(
            url_busca, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            html = resposta.read().decode('utf-8')
            
        links_v = re.findall(r'watch\?v=([^"& \s]+)', html)
        if links_v and len(links_v) > 0:
            id_limpo = links_v[0]  # CORRIGIDO: Coleta estritamente o texto do primeiro ID encontrado
            print(f"Link extraído pelo DuckDuckGo: https://youtube.com{id_limpo}")
            return f"https://youtube.com{id_limpo}"
    except Exception as e:
        print(f"DuckDuckGo falhou: {str(e)}. Pulando para o backup...")

    # --- IF 2: Tentativa de Resgate via Google Vídeos ---
    try:
        print(f"Buscando link na web via Google Vídeos para: {nome_musica}")
        url_google = "https://google.com" + urllib.parse.quote(busca_termo) + "&tbm=vid"
        requisicao = urllib.request.Request(
            url_google, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            html = resposta.read().decode('utf-8')
            
        links_g = re.findall(r'url\?q=https://www\.youtube\.com/watch\?v=([^"&]+)', html)
        if links_g and len(links_g) > 0:
            id_limpo = links_g[0]  # CORRIGIDO: Coleta estritamente o texto do primeiro ID de backup
            print(f"Link extraído pelo Google Vídeos: https://youtube.com{id_limpo}")
            return f"https://youtube.com{id_limpo}"
    except Exception as e:
        print(f"Google Vídeos falhou: {str(e)}")
        
    return None

# Função interna que baixa o áudio a partir do link direto encontrado pelas buscas
def baixar_audio_por_link(link_direto):
    opcoes_download = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'http_chunk_size': 1048576, # Segmenta o download para simular tráfego comum de navegador
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
        "🎵 *Bem-vindo ao Baixador Automático de Fila!* 🎵\n\n"
        "O sistema agora pesquisa de forma invisível nos mecanismos web para baixar listas!\n\n"
        "📝 *Opção 1: Digitar no chat*\n"
        "• Envie uma música por linha (Recomendado: até 5 por vez).\n\n"
        "📁 *Opção 2: Listas grandes de texto (.txt)*\n"
        "• Envie o arquivo do Bloco de Notas para download em lote!"
    )
    await update.message.reply_text(instrucao, parse_mode="Markdown")

# Gerenciador da fila de processamento automático de lotes
async def processar_e_enviar(update: Update, linhas: list):
    if not linhas:
        await update.message.reply_text("A lista enviada está vazia.")
        return

    total = len(linhas)
    await update.message.reply_text(f"✅ Fila iniciada! Processando {total} itens via varredura web externa...")
    os.makedirs("downloads", exist_ok=True)

    for indice, item in enumerate(linhas, start=1):
        progresso = await update.message.reply_text(f"⏳ [{indice}/{total}] Identificando fontes estáveis para: {item}...")
        try:
            link_extraido = pesquisar_link_na_web(item)
            
            if not link_extraido:
                raise Exception("Mecanismos de busca não retornaram links válidos para este nome.")

            caminho_arquivo = baixar_audio_por_link(link_extraido)
            
            with open(caminho_arquivo, 'rb') as audio:
                await update.message.reply_audio(audio=audio, title=os.path.basename(caminho_arquivo))
            
            os.remove(caminho_arquivo)
            await progresso.delete()
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao processar '{item}': {str(e)}")

# Recebimento de mensagens de texto direto
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    linhas = [linha.strip() for item in texto.split('\n') if (linha := item.strip())]
    await processar_e_enviar(update, linhas)

# Recebimento de arquivos .txt em lote
async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    documento = update.message.document
    if not documento.file_name.endswith('.txt'):
        await update.message.reply_text("Por favor, envie listas apenas em formato .txt.")
        return

    arquivo_telegram = await context.bot.get_file(documento.file_id)
    caminho_temporario = f"temp_{documento.file_name}"
    await arquivo_telegram.download_to_drive(caminho_temporario)

    with open(caminho_temporario, 'r', encoding='utf-8') as f:
        linhas = [linha.strip() for item in f.readlines() if (linha := item.strip())]

    os.remove(caminho_temporario)
    await processar_e_enviar(update, linhas=linhas)

def main():
    app = Application.builder().token(TOKEN).read_timeout(120).write_timeout(120).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
    app.add_handler(MessageHandler(filters.Document.ALL, receber_arquivo))
    
    print("Serviço de lote online...")
    app.run_polling()

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")
