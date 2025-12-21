from sqlmodel import SQLModel

from app.deps import EngineDep

def create_db_and_tables(engine: EngineDep):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    

