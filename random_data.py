from abstract_lungair_data import AbstractLungairData
import random
import datetime
import time


class RandomData(AbstractLungairData):
  """This class handles generating random data for LungAir"""

  def init_data(self, num_of_patients, num_of_observations_per_patient):
    self.num_of_patients = num_of_patients
    self.num_of_observations_per_patient = num_of_observations_per_patient
    self.patient_id_counter = 0
    self.observation_id_counter = 0
    self.last_key = ''

  def generate_random_date(self):
    d = random.randint(1, int(time.time()))
    return datetime.date.fromtimestamp(d).strftime('%Y-%m-%d')

  def get_all_patients(self):
    return [0] * self.num_of_patients

  def get_patient_chart_events(self, patient_id):
    return [0] * self.num_of_observations_per_patient

  def get_patient_gender(self, patient_info):
    return random.choice(['M', 'F'])

  def get_patient_system(self):
    return 'Randomly Generated'

  def get_patient_id(self, patient_info):
    self.patient_id_counter += 1
    return self.patient_id_counter;

  def get_patient_dob(self, patient_info):
    return self.generate_random_date()

  def get_observation_item_id(self, observation_info):
    item_id = AbstractLungairData.KEY_FROM_ITEM_ID.keys()[random.randint(0, 4)]
    self.last_key = AbstractLungairData.KEY_FROM_ITEM_ID[item_id]
    return item_id

  def get_observation_row_id(self, observation_info):
    self.observation_id_counter += 1
    return self.observation_id_counter;

  def get_observation_fio2(self, observation_info):
    # Values subject to change
    return random.randint(0, 100)

  def get_observation_pip(self, observation_info):
    # Values subject to change
    return random.randint(0, 100)

  def get_observation_peep(self, observation_info):
    # Values subject to change
    return random.randint(0, 100)

  def get_observation_hr(self, observation_info):
    # Values subject to change
    return random.randint(0, 100)

  def get_observation_sao2(self, observation_info):
    # Values subject to change
    return random.randint(0, 100)

  def get_observation_unit_string(self, observation_info):
    # Will want to change this to match the value generated
    return AbstractLungairData.UNIT_CODE.keys()[random.randint(0, 2)]

  def get_observation_system(self):
    return 'Randomly Generated'

  def get_observation_time(self, observation_info):
    return self.generate_random_date()