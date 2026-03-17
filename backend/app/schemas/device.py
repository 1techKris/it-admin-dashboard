from pydantic import BaseModel

class DeviceOut(BaseModel):
    device_id: str
    type: str
    os: str
    ip: str
    cpu: int
    mem: int
    status: str

    class Config:
        from_attributes = True
