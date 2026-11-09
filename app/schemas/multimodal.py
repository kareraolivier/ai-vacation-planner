from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    provider: str
    message: str


class SpeechJsonResponse(BaseModel):
    audio_base64: str
    content_type: str
    provider: str
    message: str


class VisionResponse(BaseModel):
    text: str
    provider: str
    message: str


class MCPToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict, alias="inputSchema")

    class Config:
        populate_by_name = True


class MCPToolListResponse(BaseModel):
    tools: List[MCPToolDescriptor]
    message: str


class MCPToolCallRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    name: str
    result: dict
    message: str


class MultimodalErrorResponse(BaseModel):
    detail: str
