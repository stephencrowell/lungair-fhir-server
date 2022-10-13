import random
from collections.abc import Iterable
from .patient_data_source import PatientDataSource, Patient, Observation
    
class RandomObservation(Observation):

  def get_observation_type(self) -> Observation.ObservationType:
    return Observation.ObservationType(random.randint(0, 4))

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