import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


class CollectionStatus(str, enum.Enum):
    """Status possíveis de uma coleta de preço.

    Um erro de scraping nunca deve virar um preço 0 ou inválido — deve
    virar um desses status, para o frontend distinguir "preço realmente
    caiu" de "não conseguimos coletar".
    """

    SUCCESS = "SUCCESS"
    PRICE_NOT_FOUND = "PRICE_NOT_FOUND"
    PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class Product(Base):
    """Produto da própria empresa que se deseja monitorar na concorrência."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    ean = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    monitored_products = relationship(
        "MonitoredProduct", back_populates="product", cascade="all, delete-orphan"
    )


class MonitoredProduct(Base):
    """Vínculo entre um produto e a URL onde ele é monitorado em um concorrente.

    Um mesmo `product` pode ter várias entradas aqui — uma por concorrente.
    A URL só existe aqui depois que o usuário confirmou, na etapa de
    pesquisa/matching, que aquele resultado é realmente o produto certo.
    """

    __tablename__ = "monitored_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    competitor = Column(String, nullable=False)
    url = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="monitored_products")
    price_history = relationship(
        "PriceHistory", back_populates="monitored_product", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    """Cada linha é uma coleta — inclusive quando ela falha (ver `status`)."""

    __tablename__ = "price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitored_product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitored_products.id"),
        nullable=False,
        index=True,
    )
    price = Column(Numeric(10, 2), nullable=True)  # nulo quando status != SUCCESS
    status = Column(
        Enum(CollectionStatus), default=CollectionStatus.SUCCESS, nullable=False
    )
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    monitored_product = relationship("MonitoredProduct", back_populates="price_history")


class Settings(Base):
    """Configuração do sistema — registro único (linha 'singleton').

    A frequência do scheduler é definida aqui pela empresa através do
    frontend, e não fixada no código.
    """

    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scrape_frequency_minutes = Column(Numeric, nullable=False, default=360)  # padrão: 6h
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
