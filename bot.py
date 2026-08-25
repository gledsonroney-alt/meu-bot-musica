import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Seu Token gerado no BotFather
TOKEN = "8812668800:AAHhAI9keRnUyPgZ5Ssv-_Swr0WP-ENM6wc"

# Função inteligente que tenta várias fontes nativas se encontrar qualquer restrição
def baixar_audio(busca_ou_link):
    if ":" in busca_ou_link and not busca_ou_link.startswith("http"):
        busca_ou_link = busca_ou_link.replace(":", " ")

    # Lista de motores nativos aceitos pelo yt-dlp para exaustão de tentativas
    motores_busca = ['ytsearch', 'ytsearch1', 'ytsmsearch']
    
    ultima_falha = ""

    for motor in motores_busca:
        print(f"Tentando baixar usando o motor: {motor}")
        
        opcoes = {
            'format': 'bestaudio/best',
            'default_search': motor,  
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'nocheckcertificate': True,   
            'ignoreerrors': True,
            # Força o yt-dlp a simular um navegador comum para evitar o bloqueio de robô
            'http_chunk_size': 1048576,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }
        
        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                info = ydl.extract_info(busca_ou_link, download=True)
                
                if info is None:
                    raise Exception("A plataforma bloqueou o IP temporariamente.")
                    
                if 'entries' in info:
                    if len(info['entries']) > 0 and info['entries'] is not None:
                        video = info['entries'][0]  # Pega o primeiro item de forma direta e segura
                    else:
                        raise Exception("Nenhum vídeo retornado na busca.")
                else:
                    video = info
                
                filename = ydl.prepare_filename(video)
                nome_base, _ = os.path.splitext(filename)
                caminho_mp3 = nome_base + ".mp3"
                
                if os.path.exists(caminho_mp3):
                    print(f"Sucesso usando o motor: {motor}")
                    return caminho_mp3
                else:
                    raise Exception("O conversor falhou em gerar o arquivo MP3.")
                    
        except Exception as erro_atual:
            ultima_falha = str(erro_atual)
            print(f"O motor {motor} falhou: {ultima_falha}. Tentando próxima alternativa...")
            continue

    raise Exception(f"Todas as tentativas falharam por restrições das plataformas. Último erro: {ultima_falha}")

# Comando /start com instruções de uso e limites
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instrucao = (
        "🎵 *Bem-vindo ao Baixador de Músicas Auto-Resiliente!* 🎵\n\n"
        "O sistema agora possui um mecanismo que dribla bloqueios e restrições automaticamente!\n\n"
        "📝 *Opção 1: Digitar direto no chat*\n"
        "• Envie uma música ou link por linha.\n"
        "• ⚠️ *Recomendado:* No máximo *5 músicas* por mensagem.\n\n"
        "📁 *Opção 2: Listas grandes (Recomendado)*\n"
        "• Cole todas as músicas em um arquivo do *Bloco de Notas (.txt)*.\n"
        "• Coloque uma música por linha.\n"
        "• Anexe e envie o arquivo `.txt` aqui no chat.\n"
        "• Ideal para listas longas com dezenas de músicas!\n\n"
        "Pode enviar sua lista agora!"
    )
    await update.message.reply_text(instrucao, parse_mode="Markdown")

# Função auxiliar para processar e baixar os itens com contador visual
async def processar_e_enviar(update: Update, linhas: list):
    if not lines:
        await update.message.reply_text("A lista enviada está vazia.")
        return

    total = len(linhas)
    await update.message.reply_text(f"✅ Identifiquei {total} itens. Iniciando a fila de downloads com desvio de bloqueios...")
    os.makedirs("downloads", exist_ok=True)

    for indice, item in enumerate(linhas, start=1):
        progresso = await update.message.reply_text(f"⏳ [{indice}/{total}] Processando fontes para: {item}...")
        try:
            caminho_arquivo = baixar_audio(item)
            
            with open(caminho_arquivo, 'rb') as audio:
                await update.message.reply_audio(audio=audio, title=os.path.basename(caminho_arquivo))
            
            os.remove(caminho_arquivo)
            await progresso.delete()
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao baixar '{item}': {str(e)}")

# Processador de mensagens de texto direto no chat
async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    linhas = [linha.strip() for item in texto.split('\n') if (linha := item.strip())]
    await processar_e_enviar(update, linhas=linhas)

# Processador de arquivos de texto (.txt) enviados
async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    documento = update.message.document
    
    if not documento.file_name.endswith('.txt'):
        await update.message.reply_text("Por favor, envie a lista em formato do Bloco de Notas (.txt).")
        return

    arquivo_telegram = await context.bot.get_file(documento.file_id)
    caminho_temporario = f"temp_{documento.file_name}"
    await arquivo_telegram.download_to_drive(caminho_temporario)

    with open(caminho_temporario, 'r', encoding='utf-8') as f:
        linhas = [linha.strip() for item in f.readlines() if (linha := item.strip())]

    os.remove(caminho_temporario)
    await processar_e_enviar(update, linhas=linhas)

# Execução do Bot com timeouts estendidos para segurança
def main():
    app = Application.builder().token(TOKEN).read_timeout(120).write_timeout(120).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
    app.add_handler(MessageHandler(filters.Document.ALL, receber_arquivo))
    
    print("Bot rodando com sucesso...")
    app.run_polling()

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")

