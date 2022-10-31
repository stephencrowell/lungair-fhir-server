import random
from collections.abc import Iterable
from data_sources.patient_data_source import PatientDataSource, Patient, Observation
    
class RandomObservation(Observation):
  def get_observation_type(self) -> str:
    return random.choice(['FIO2', 'PIP', 'PEEP', 'HR', 'SAO2', 'bodyweight'])

  def get_value(self) -> str:
    return random.randint(0, 100)


class RandomDataSource(PatientDataSource):
  """This class handles generating random data"""

  def __init__(self, num_of_patients, num_of_observations_per_patient):
    self.num_of_patients = num_of_patients
    self.num_of_observations_per_patient = num_of_observations_per_patient


  def get_all_patients(self) -> Iterable[Patient]:
    return (Patient() for _ in range(self.num_of_patients))

  def get_patient_observations(self, patient : Patient) -> Iterable[Observation]:
    return (RandomObservation() for _ in range(self.num_of_observations_per_patient))