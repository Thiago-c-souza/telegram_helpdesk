from typing import List, Optional
from sqlalchemy.orm import Session
from models import Usuario, Ticket

# ==== USUÁRIO ====
def criar_usuario(db: Session, nome: str, email: str) -> Usuario:
    u = Usuario(nome=nome, email=email)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def obter_usuario_por_id(db: Session, user_id: int) -> Optional[Usuario]:
    return db.get(Usuario, user_id)

def listar_usuarios(db: Session) -> List[Usuario]:
    return db.query(Usuario).all()

def atualizar_usuario(db: Session, user_id: int, nome: Optional[str] = None, email: Optional[str] = None) -> Optional[Usuario]:
    u = db.get(Usuario, user_id)
    if not u:
        return None
    if nome is not None:
        u.nome = nome
    if email is not None:
        u.email = email
    db.commit()
    db.refresh(u)
    return u

def deletar_usuario(db: Session, user_id: int) -> bool:
    u = db.get(Usuario, user_id)
    if not u:
        return False
    db.delete(u)
    db.commit()
    return True

# ==== TICKET ====
def criar_ticket(db: Session, usuario_id: int, titulo: str, descricao: str = "", status: str = "aberto") -> Ticket:
    t = Ticket(usuario_id=usuario_id, titulo=titulo, descricao=descricao, status=status)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

def listar_tickets(db: Session) -> List[Ticket]:
    return db.query(Ticket).all()

def listar_tickets_por_usuario(db: Session, usuario_id: int) -> List[Ticket]:
    return db.query(Ticket).filter(Ticket.usuario_id == usuario_id).all()

def atualizar_ticket(db: Session, ticket_id: int, **campos) -> Optional[Ticket]:
    t = db.get(Ticket, ticket_id)
    if not t:
        return None
    for k, v in campos.items():
        if hasattr(t, k) and v is not None:
            setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t

def deletar_ticket(db: Session, ticket_id: int) -> bool:
    t = db.get(Ticket, ticket_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True
