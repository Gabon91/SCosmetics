from pydantic import BaseModel, ConfigDict


class TreatmentRead(BaseModel):
    id: int
    name: str
    category: str
    description: str
    duration_minutes: int
    price: float
    accent: str

    model_config = ConfigDict(from_attributes=True)

