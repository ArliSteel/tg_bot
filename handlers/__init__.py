from .base import register_base_handlers
from .faq import register_faq_handlers
from .messages import register_message_handlers

__all__ = [
    'register_base_handlers',
    'register_faq_handlers', 
    'register_message_handlers'
]