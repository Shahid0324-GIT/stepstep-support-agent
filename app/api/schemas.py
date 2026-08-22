from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    request_id: str
    response: str