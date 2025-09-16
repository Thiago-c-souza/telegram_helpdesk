from contextlib import contextmanager
from database import ENGINE, SessionLocal
from models import Base
import crud

# Cria as tabelas (somente na primeira execução ou quando mudar os models)
Base.metadata.create_all(bind=ENGINE)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    with get_db() as db:
        # CREATE
        u1 = crud.criar_usuario(db, nome="Luís", email="luis@exemplo.com")
        u2 = crud.criar_usuario(db, nome="Jamilly", email="jamilly@exemplo.com")

        t1 = crud.criar_ticket(db, usuario_id=u1.id, titulo="Erro NF-e", descricao="CEAN inválido", status="aberto")
        t2 = crud.criar_ticket(db, usuario_id=u1.id, titulo="Falha na impressão", descricao="Impressora Zebra", status="em análise")

        # READ
        print("Usuários:", [ (u.id, u.nome, u.email) for u in crud.listar_usuarios(db) ])
        print("Tickets do Luís:", [ (t.id, t.titulo, t.status) for t in crud.listar_tickets_por_usuario(db, u1.id) ])

        # UPDATE
        crud.atualizar_usuario(db, u1.id, nome="Luís Eduardo")
        crud.atualizar_ticket(db, t1.id, status="resolvido", descricao="Cliente atualizou CEAN")

        # DELETE
        crud.deletar_ticket(db, t2.id)
        # crud.deletar_usuario(db, u1.id) deletaria o usuário e os tickets (por causa do cascade)
