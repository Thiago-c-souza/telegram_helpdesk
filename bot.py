import os
from contextlib import contextmanager
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from database import SessionLocal
import crud

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Gerenciador de sessão por handler ---
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helpers simples ---
def parse_pipe_args(text: str, expected_parts: int):
    """
    /comando arg1 | arg2 | arg3
    Retorna lista com tamanho esperado, preenchendo com "" se faltar.
    """
    # remove o comando
    parts = text.split(" ", 1)
    payload = parts[1] if len(parts) > 1 else ""
    items = [p.strip() for p in payload.split("|")]
    items += [""] * (expected_parts - len(items))
    return items[:expected_parts]

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Bem-vindo ao Bot do Helpdesk! 🤖\n\n"
        "Comandos rápidos:\n"
        "/add_usuario Nome | email\n"
        "/usuarios\n"
        "/novo_ticket email_do_usuario | título | descrição\n"
        "/tickets email_do_usuario\n"
        "/atualizar_ticket id | status=novo_status | descricao=nova_desc\n"
        "/deletar_ticket id\n"
        "\nDica: use o caractere '|' para separar campos."
    )
    await update.message.reply_text(msg)

async def add_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nome, email = parse_pipe_args(update.message.text, 2)
        if not nome or not email:
            return await update.message.reply_text("Uso: /add_usuario Nome | email")
        with get_db() as db:
            u = crud.criar_usuario(db, nome=nome, email=email)
            await update.message.reply_text(f"✅ Usuário criado: {u.id} - {u.nome} ({u.email})")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao criar usuário: {e}")

async def usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_db() as db:
        lista = crud.listar_usuarios(db)
        if not lista:
            return await update.message.reply_text("Nenhum usuário cadastrado.")
        linhas = [f"{u.id} - {u.nome} ({u.email})" for u in lista]
        await update.message.reply_text("👥 Usuários:\n" + "\n".join(linhas))

async def novo_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email, titulo, descricao = parse_pipe_args(update.message.text, 3)
        if not email or not titulo:
            return await update.message.reply_text("Uso: /novo_ticket email | título | descrição(opcional)")
        with get_db() as db:
            # Procurar usuário pelo email
            usuarios = [u for u in crud.listar_usuarios(db) if u.email == email]
            if not usuarios:
                return await update.message.reply_text("❌ Usuário não encontrado para esse email.")
            usuario = usuarios[0]
            t = crud.criar_ticket(db, usuario_id=usuario.id, titulo=titulo, descricao=descricao or "", status="aberto")
            await update.message.reply_text(f"🎫 Ticket criado: #{t.id} - {t.titulo} (status: {t.status})")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao criar ticket: {e}")

async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = None
    parts = update.message.text.split(" ", 1)
    if len(parts) > 1:
        email = parts[1].strip()
    with get_db() as db:
        if email:
            usuarios = [u for u in crud.listar_usuarios(db) if u.email == email]
            if not usuarios:
                return await update.message.reply_text("Usuário não encontrado para esse email.")
            usuario = usuarios[0]
            lista = crud.listar_tickets_por_usuario(db, usuario.id)
        else:
            lista = crud.listar_tickets(db)

        if not lista:
            return await update.message.reply_text("Nenhum ticket encontrado.")

        # Opcional: teclado inline para ações rápidas por ticket
        for t in lista:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Resolvido", callback_data=f"resolve:{t.id}"),
                 InlineKeyboardButton("🗑️ Deletar", callback_data=f"delete:{t.id}")]
            ])
            await update.message.reply_text(
                f"#{t.id} | {t.titulo}\nStatus: {t.status}\nDesc: {t.descricao[:120]}",
                reply_markup=keyboard
            )

async def atualizar_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # /atualizar_ticket id | status=novo | descricao=xxx
        id_str, campo1, campo2 = parse_pipe_args(update.message.text, 3)
        if not id_str:
            return await update.message.reply_text("Uso: /atualizar_ticket id | status=novo_status | descricao=texto")
        ticket_id = int(id_str)
        campos = {}
        for c in (campo1, campo2):
            if "=" in c:
                k, v = c.split("=", 1)
                campos[k.strip()] = v.strip()

        with get_db() as db:
            t = crud.atualizar_ticket(db, ticket_id, **campos)
            if not t:
                return await update.message.reply_text("Ticket não encontrado.")
            await update.message.reply_text(f"✏️ Ticket #{t.id} atualizado. Status: {t.status}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def deletar_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(" ", 1)
        if len(parts) < 2:
            return await update.message.reply_text("Uso: /deletar_ticket id")
        ticket_id = int(parts[1].strip())
        with get_db() as db:
            ok = crud.deletar_ticket(db, ticket_id)
            await update.message.reply_text("🗑️ Deletado." if ok else "Ticket não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

# --- Callbacks de botões inline ---
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    try:
        action, id_str = data.split(":", 1)
        ticket_id = int(id_str)
    except Exception:
        return await query.edit_message_text("Ação inválida.")

    if action == "resolve":
        with get_db() as db:
            t = crud.atualizar_ticket(db, ticket_id, status="resolvido")
            if not t:
                return await query.edit_message_text("Ticket não encontrado.")
            await query.edit_message_text(f"✅ Ticket #{t.id} marcado como resolvido.")
    elif action == "delete":
        with get_db() as db:
            ok = crud.deletar_ticket(db, ticket_id)
            await query.edit_message_text("🗑️ Ticket deletado." if ok else "Ticket não encontrado.")

# --- Bootstrap ---
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Defina TELEGRAM_TOKEN no .env")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_usuario", add_usuario))
    app.add_handler(CommandHandler("usuarios", usuarios))
    app.add_handler(CommandHandler("novo_ticket", novo_ticket))
    app.add_handler(CommandHandler("tickets", tickets))
    app.add_handler(CommandHandler("atualizar_ticket", atualizar_ticket))
    app.add_handler(CommandHandler("deletar_ticket", deletar_ticket))
    app.add_handler(CallbackQueryHandler(on_button))

    # opcional: responder qualquer mensagem não-comando
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    print("Bot rodando. Pressione Ctrl+C para sair.")
    app.run_polling()

if __name__ == "__main__":
    main()
