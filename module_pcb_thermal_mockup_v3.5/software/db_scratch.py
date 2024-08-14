
import env
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import data_models as dm 

engine = create_engine( getattr(env, "DATABASE_URI"), echo=True )

# creates and drops all tables
# dm.Base.metadata.drop_all(engine)
# dm.Base.metadata.create_all(engine)

#adds module
# with Session(engine) as session:
#     mod = dm.Module(
#         name="TM0001",
#     )
#     session.add(mod)
#     session.commit()