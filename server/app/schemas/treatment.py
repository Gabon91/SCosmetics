from pydantic import BaseModel, ConfigDict, Field


class TreatmentRead(BaseModel):
    id: int
    name: str
    category: str
    description: str
    duration_minutes: int = Field(gt=0, multiple_of=15)
    price: float
    accent: str

    model_config = ConfigDict(from_attributes=True)
