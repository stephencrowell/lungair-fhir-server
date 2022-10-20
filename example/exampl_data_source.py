from collections.abc import Iterable
from .patient_data_source import PatientDataSource, Patient, Observation
import pandas as pd
 
class ExamplePatient(Patient):

  def __init__(self, patient_info):
    self.patient_info = patient_info

  def get_indentifier_value(self) -> str:
    return str(self.patient_info['patient_id'])

class ExampleObservation(Observation):

  def __init__(self, observation_info):
    self.observation_info = observation_info

  def get_observation_type(self) -> str:
    return 'bodyweight'

  def get_value(self) -> str:
    return self.observation_info['bodyweight']


class ExampleDataSource(PatientDataSource):

  def __init__(self, csv_file):
    self.data = pd.read_csv(csv_file)


  def get_all_patients(self) -> Iterable[Patient]:
    mask1 = df['patient_id'].duplicated(keep = 'first') # Get first occurance of patient_id
    mask2 = df['patient_id'].duplicated(keep = False) # Mark duplicate patient_ids
    mask = not mask1 or not mask2
    return (ExamplePatient(row) for _, row in self.data.iterrows())

  def get_patient_observations(self, patient : Patient) -> Iterable[Observation]:
    return (ExampleObservation(row) for _, row in self.data[self.data['patient_id'] = patient.get_indentifier_value()].iterrows())