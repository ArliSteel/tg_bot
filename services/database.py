import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, BigInteger, Text, DateTime, func

from config import load_config

logger = logging.getLogger(__name__)

# Загружаем конфиг
config = load_config()

# Создаем движок и сессии
engine = create_async_engine(
    config.database_url,
    echo=False,  # Поставьте True для отладки SQL запросов
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Базовая модель для всех таблиц
class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Модель для логов сообщений
class MessageLog(BaseModel):
    __tablename__ = "message_logs"
    
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(Text)
    chat_id = Column(BigInteger, nullable=False)
    message_text = Column(Text)
    message_type = Column(Text, default="text")
    is_bot_response = Column(Integer, default=0)  # 0 - сообщение пользователя, 1 - ответ бота

async def init_database():
    """Инициализация базы данных - создание таблиц"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

async def log_user_message(user_id: int, username: str, chat_id: int, message_text: str):
    """Логирование сообщения пользователя"""
    try:
        async with AsyncSessionLocal() as session:
            message = MessageLog(
                user_id=user_id,
                username=username,
                chat_id=chat_id,
                message_text=message_text,
                message_type="text",
                is_bot_response=0
            )
            session.add(message)
            await session.commit()
            return message.id
    except Exception as e:
        logger.error(f"Ошибка логирования сообщения: {e}")

async def log_bot_response(user_id: int, chat_id: int, response_text: str):
    """Логирование ответа бота"""
    try:
        async with AsyncSessionLocal() as session:
            message = MessageLog(
                user_id=user_id,
                chat_id=chat_id,
                message_text=response_text,
                message_type="text", 
                is_bot_response=1
            )
            session.add(message)
            await session.commit()
            return message.id
    except Exception as e:
        logger.error(f"Ошибка логирования ответа бота: {e}")