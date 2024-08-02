#GUI for control board

from sqlalchemy import create_engine

import env
val = getattr(env, "DATABASE_URI")

engine = create_engine(val, echo=True)

print("hello world")

 