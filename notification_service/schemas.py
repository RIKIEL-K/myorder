from pydantic import BaseModel

class EmailSchema(BaseModel):
    email_destinataire: str
    message: str
