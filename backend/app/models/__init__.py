"""Model registration. Importing this module registers all ORM classes with
SQLAlchemy's metadata, which Alembic needs for autogenerate to work."""
from app.models.user import User
from app.models.product import Product
from app.models.interaction import Interaction
from app.models.cart import CartEvent
from app.models.episode import ModelEpisode
from app.models.model_registry import ModelRegistry

__all__ = [
    "User",
    "Product",
    "Interaction",
    "CartEvent",
    "ModelEpisode",
    "ModelRegistry",
]