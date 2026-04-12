"""Job de expiração de estados conversacionais stale."""
import logging

from app.database import SessionLocal
from app.services.conversation_state import ConversationStateService

logger = logging.getLogger(__name__)


async def run_expire_states():
    """Executa a expiração de estados stale.

    Abre uma sessão própria, instancia o serviço e marca estados
    expirados como consumidos.
    """
    session = None
    try:
        session = SessionLocal()
        service = ConversationStateService(session)
        count = service.expire_stale_states()
        logger.info("Expired %d stale conversation states", count)
    except Exception as e:
        logger.exception("Error expiring stale states: %s", e)
    finally:
        if session:
            session.close()