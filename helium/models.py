from pydantic import BaseModel, Field


class HeliumSynthesis(BaseModel):
    diagnosis: str = Field(min_length=1)
    remediation: str = Field(min_length=1)
