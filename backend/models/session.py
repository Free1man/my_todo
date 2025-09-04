from pydantic import BaseModel

from .mission import Mission


class TBSSession(BaseModel):
    id: str
    mission: Mission
