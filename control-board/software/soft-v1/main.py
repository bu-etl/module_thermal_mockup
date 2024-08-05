#GUI for control board

from sqlalchemy import create_engine

import env
val = getattr(env, "DATABASE_URI")

engine = create_engine(val, echo=True)

from database.models import create_all

create_all(engine)

print("hello world")