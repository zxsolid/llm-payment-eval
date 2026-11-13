from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentExtraction(BaseModel):
    """Что модель должна вернуть по одному сообщению.

    Все поля обязательные: модель должна вписать каждое, значение или null.
    Если поле необязательное, маленькая модель просто пропускает его, и это
    выглядит как «суммы в тексте нет».
    """

    model_config = ConfigDict(extra="forbid")

    amount: Optional[str] = Field(
        ..., description="Сумма без комиссии, число с точкой и двумя знаками: 15000.00. null, если суммы нет."
    )
    currency: Optional[Literal["RUB", "USD", "EUR", "KZT", "UZS", "CNY"]] = Field(
        ..., description="ISO-код валюты. null, если суммы нет."
    )
    counterparty: Optional[str] = Field(
        ..., description="Кому платим, а при возврате кто вернул. Как в тексте, без кавычек. null, если не указан."
    )
    purpose: Optional[str] = Field(..., description="Назначение платежа коротко, словами из текста.")
    invoice_number: Optional[str] = Field(..., description="Номер счёта или договора без знака №. null, если нет.")
    date: Optional[str] = Field(
        ..., description="Дата в формате YYYY-MM-DD. null, если даты нет, она относительная или без года."
    )
    operation: Literal["payment", "refund"] = Field(..., description="payment — оплата, refund — возврат денег нам.")

    @field_validator("amount", "currency", "counterparty", "purpose", "invoice_number", "date", mode="before")
    @classmethod
    def _blank_is_null(cls, v):
        # Пустая строка значит то же, что null: значения нет.
        return None if isinstance(v, str) and not v.strip() else v
