import random
import time
from datetime import datetime
from collections.abc import Iterable
from patient_data_source import PatientDataSource, Patient, Observation

class RandomPatient(Patient):

  def __init__(self, id : int):
    self.id = id

  def get_gender(self) -> Patient.Gender:  
    return Patient.Gender[random.randint(0, 3)]

  def get_identifier_value(self) -> str:
    return str(self.id)

  def get_identifier_system(self) -> str:
    return 'Randomly Generated'

  def get_dob(self) -> datetime:
    d = random.randint(1, int(time.time()))
    return datetime.date.fromtimestamp(d)
    

class RandomObservation(Observation):

  def __init__(self, id : int, patient : Patient):
    self.id = id
    self.patient = patient

  def get_identifier_value(self) -> str:
    return str(self.id)

  def get_identifier_system(self) -> str:
    return 'Randomly Generated'

  def get_observation_type(self) -> Observation.ObservationType:
    return Observation.ObservationType[random.randint(0, 4)]

  def get_value(self) -> str:
    return random.randint(0, 100)

  def get_time(self) -> datetime:
    d = random.randint(int(self.patient.get_dob().timestamp()), int(time.time()))
    return datetime.date.fromtimestamp(d)


class RandomData(PatientDataSource):
  """This class handles generating random data for LungAir"""

  def __init__(self, num_of_patients, num_of_observations_per_patient):
    self.num_of_patients = num_of_patients
    self.num_of_observations_per_patient = num_of_observations_per_patient


  def get_all_patients(self) -> Iterable[Patient]:
    return (Patient(i) for i in range(self.num_of_patients))

  def get_patient_observations(self, patient : Patient) -> Iterable[Observation]:
    return (Observation(i, patient) for i in range(self.num_of_observations_per_patient))