
import env
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import Session
import data_models as dm 
from datetime import datetime
engine = create_engine( getattr(env, "DATABASE_URI"), echo=True )

# creates and drops all tables
# dm.Base.metadata.drop_all(engine)
# dm.Base.metadata.create_all(engine)

#adds module
with Session(engine) as session:
    query = select(dm.Module).where(dm.Module.name == 'TM0001')
    module = session.scalars(query).one()

    query2 = select(dm.Run).where(dm.Run.id == 2)
    run = session.scalars(query2).one()
    db_data = dm.Data(
        module = module,
        sensor = 3,
        timestamp = datetime.now(),
        raw_adc = 'hey',
        volts = 123.3,
        ohms = 30.2,
        celcius = 33.3,
        run = run
    )

# get run sqlalchemy obj -> keep same, specific set, or new

#run = NEW comment="this is a long comment blah blah" Mode = TEST/DEBUG/REAL
#run = 4