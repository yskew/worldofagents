from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.human import Human  # noqa: E402, F401
from app.models.agent import Agent  # noqa: E402, F401
from app.models.verification_log import VerificationLog  # noqa: E402, F401
