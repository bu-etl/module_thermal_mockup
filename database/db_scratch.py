
from env import DATABASE_URI
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import Session
import models as dm 
from datetime import datetime
engine = create_engine(DATABASE_URI, echo=False )


# ------------ ADD Cold plate to cold plate table ------------ #
# with Session(engine) as session:
#     query = select(dm.Module).where(dm.Module.name == 'TM0001')
#     thermal_mockup = session.execute(query).scalars().first()

#     # # add Cold Plate configuration (epoxy and solder v1 and solder v2)
#     with open("/home/hayden/Downloads/Solder_and_Epoxy_Plate.png", 'rb') as f:
#         solder_and_epoxy_plate_image = f.read()
#     epoxy_plate = dm.ColdPlate(
#         name='Epoxy Plate v1',
#         positions = {
#             '1': 'front side, far left',
#             '2': 'front side, middle',
#             '3': 'front side, far right',
#             '4': 'back side, far left',
#             '5': 'back side, middle',
#             '6': 'back side, far right',
#         },
#         plate_image = solder_and_epoxy_plate_image,
#     )
#     solder_plate = dm.ColdPlate(
#         name='Solder Plate v1',
#         positions = {
#             '1': 'front side, far left',
#             '2': 'front side, middle',
#             '3': 'front side, far right',
#             '4': 'back side, far left',
#             '5': 'back side, middle',
#             '6': 'back side, far right',
#         },
#         plate_image = solder_and_epoxy_plate_image,
#     )

#     session.add(epoxy_plate)
#     session.add(solder_plate)

#     session.commit()
#-------------------------------------------------------------#

# ------------ ADD COLD PLATE TO RUNS ------------ #
# with Session(engine) as session:
#     query = select(dm.ColdPlate).where(dm.ColdPlate.name == 'Epoxy Plate v1')
#     epoxy_plate = session.execute(query).scalars().first()

#     query = select(dm.ColdPlate).where(dm.ColdPlate.name == 'Solder Plate v1')
#     solder_plate = session.execute(query).scalars().first()

#     runs = select(dm.Run)
#     for run in session.execute(runs).scalars().all():
#         if run.id <= 8:
#             run.cold_plate = epoxy_plate
#         elif run.id > 8 and run.id != 14:
#             run.cold_plate = solder_plate
#     session.commit()
#-------------------------------------------------------------#


# ------------ Add plate position to data table ------------ #
# with Session(engine) as session:
#     for run in session.execute(select(dm.Run)).scalars().all():
#         if run.id == 3 or run.id == 4:
#             for data in run.data:
#                 data.plate_position = 5
#         elif run.id == 7 or run.id == 8:
#             for data in run.data:
#                 data.plate_position = 2
#         elif run.id == 12:
#             for data in run.data:
#                 data.plate_position = 5
#         elif run.id == 14:
#             for data in run.data:
#                 data.plate_position = 2
# -------------------------------------------------------------#

# ------------ Checking data was inserted and the hybrid property ------------ #
# with Session(engine) as session:
#     query = select(dm.Run).where(dm.Run.id == 14)
#     run = session.execute(query).scalars().first()
    
#     all_data = run.data

#     d = all_data[0]
#     print(d.plate_position)
#     print(d.volts)
#     print(d.volts_calc)
    
#     print(d.ohms)
#     print(d.ohms_calc)
        
# -------------------------------------------------------------#

# ----------------- Adding Calibration Data ------------------ #
# with Session(engine) as session:
#     query = select(dm.Module).where(dm.Module.name == 'TM0001')
#     thermal_mockup = session.execute(query).scalars().first()
    
#     E1_calibration = dm.SensorCalibration(
#         module = thermal_mockup,
#         sensor = 'E1',
#         fit_ohms_over_celcius = 3.6682463501270317,
#         fit_ohms_intercept = 740.9934812257274
#     )

#     E3_calibration = dm.SensorCalibration(
#         module = thermal_mockup,
#         sensor = 'E3',
#         fit_ohms_over_celcius = 3.0341696569667955,
#         fit_ohms_intercept = 723.5081039009991
#     )

#     E4_calibration = dm.SensorCalibration(
#         module = thermal_mockup,
#         sensor = 'E4',
#         fit_ohms_over_celcius = 3.0846916504139346,
#         fit_ohms_intercept = 735.6945560895681
#     )

#     L4_calibration = dm.SensorCalibration(
#         module = thermal_mockup,
#         sensor = 'L4',
#         fit_ohms_over_celcius = 3.5332573008093036,
#         fit_ohms_intercept = 843.5650697047028
#     )

#     session.add(E1_calibration)
#     session.add(E3_calibration)
#     session.add(E4_calibration)
#     session.add(L4_calibration)

#     mod_calib = dm.ModuleCalibration(
#         E1 = E1_calibration,
#         E3 = E3_calibration,
#         E4 = E4_calibration,
#         L4 = L4_calibration,
#         module = thermal_mockup,
#         comment="This is the first calibration for the thermal mockup that was done by Hayden and Naomi at 904 BTL coldbox"
#     )
#     session.add(mod_calib)
#     session.commit()

# ............... Recalibration data for thermal mockup 1
# import json
# with Session(engine) as session:
#     query = select(dm.Module).where(dm.Module.name == 'TM0001')
#     thermal_mockup = session.execute(query).scalars().first()
    
#     with open("/home/hayden/repos/module_pcb_thermal_mockup/module_pcb_thermal_mockup_v3.5/software/CalibrationGUI/calibration_data_TM0001_2024-09-16 13:25:57.037017.json", 'r') as f:
#         calib_data = json.load(f)

#     db_calibs = []
#     for sensor in ['E1','E3','E4']:
#         db_calibs.append(
#             dm.SensorCalibration(
#                 module = thermal_mockup,
#                 sensor = sensor,
#                 fit_ohms_over_celcius = calib_data[sensor]['fit_slope'],
#                 fit_ohms_intercept = calib_data[sensor]['fit_intercept'],
#                 celcius = calib_data[sensor]['temps'],
#                 ohms = calib_data[sensor]['ohms'],
#                 raw_adc = calib_data[sensor]['raw_adcs'],
#                 times = calib_data[sensor]['times'],
#                 all_raw_adcs = calib_data[sensor]['all_raw_adcs'],
#                 all_raw_times = calib_data[sensor]['all_times'],
#             )
#         )
    
#     session.add_all(db_calibs)

#     mod_recalib = dm.ModuleCalibration(
#         E1 = db_calibs[0],
#         E3 = db_calibs[1],
#         E4 = db_calibs[2],
#         module = thermal_mockup,
#         comment="This is the recalibration for the thermal mockup that was done by Hayden at IRRAD"
#     )

#     session.add(mod_recalib)

#     thermal_mockup.calibration = mod_recalib

#     session.commit()