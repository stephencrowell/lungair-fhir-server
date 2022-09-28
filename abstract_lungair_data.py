from abc import ABC, abstractmethod
import names
import warnings
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation

class AbstractLungairData(ABC):
	"""Abstract class for loading patient data into a smart FHIR server"""
	def __init__(self):
		self.FHIR_DATETIME_FORMAT_STRING = '%Y-%m-%dT%H:%M:%S-05:00'

		# see https://www.hl7.org/fhir/valueset-administrative-gender.html
		self.FHIR_GENDER_MAPPING = {'M':'male', 'F':'female'}

		# LOINC codes that I found by using loinc.org/search/ ... and making my best guesses when things were unclear
		# Not to be fully trusted
		self.LOINC_CODES = {
		  'fio2' : '19996-8',
		  'pip' : '60951-1',
		  'peep' : '20077-4',
		  'hr' : '8867-4',
		  'sao2' : '59408-5',
		}

	    # The item ID of each chart event that we support exporting to the fhir server
	    # These IDs were determined by exploring the D_ITEMS table; see https://mimic.mit.edu/docs/iii/tables/d_items/
		self.ITEM_IDS = {
		  'fio2' : 3420,
		  'pip' : 507,
		  'peep' : 505,
		  'hr' : 211,
		  'sao2' : 834,
		}

	    # Map unit strings from the VALUEUOM column of CHARTEVETS to codes that follow the spec in
	    # https://ucum.org/ucum.html
		self.UNIT_CODE = {
	      'bpm':'/min',
		  'cmH20':'cm[H2O]',
		  '%':'%',
		}

		# Inverse of the ITEM_IDS mapping
		self.KEY_FROM_ITEM_ID = {v:k for k,v in self.ITEM_IDS.items()}

	@abstractmethod
	def get_all_patients(self):
		"""Returns a list of all patients."""
		pass

	@abstractmethod
	def get_patient_chart_events(self, patient_id):
		"""Returns a list of all Chart Events for one patient."""
		pass

	@abstractmethod
	def get_patient_gender(self, patient_info):
		"""Returns the patient's gender."""		
		pass

	@abstractmethod
	def get_patient_system(self):
		"""Returns the system where the patient information is stored."""		
		pass

	@abstractmethod
	def get_patient_id(self, patient_info):
		"""Returns the patient's id."""
		pass

	@abstractmethod
	def get_patient_dob(self, patient_info):
		"""Returns the patient's DOB."""
		pass

	def generate_name(self, gender):
		"""Returns a first and last name based on gender."""
	  return names.get_last_name(), names.get_first_name('male' if gender=='M' else 'female')

	def create_patient(self, patient_info):
		"""Create a smart Patient object."""
		gender = self.get_patient_gender(patient_info)
		family, given = self.generate_name(gender)
		return Patient({
		  'gender' : self.FHIR_GENDER_MAPPING[gender],
		  'identifier' : [
		    {
		      'system' : self.get_patient_system(),
		      'value' : str(self.get_patient_id(patient_info)),
		    }
		  ],
		  'birthDate' : self.get_patient_dob(patient_info).strftime('%Y-%m-%d'),
		  'name' : [{'family':family,'given':[given]}],
		})

	@abstractmethod
	def get_observation_item_id(self, observation_info):
		"""Returns the observation id."""
		pass

	@abstractmethod
	def get_observation_row_id(self, observation_info):
		"""Returns the observation row id."""
		pass

	@abstractmethod
	def get_observation_fio2(self, observation_info):
		"""Returns the observation fio2 value."""
		pass

	@abstractmethod
	def get_observation_pip(self, observation_info):
		"""Returns the observation pip value."""
		pass

	@abstractmethod
	def get_observation_peep(self, observation_info):
		"""Returns the observation peep value."""
		pass

	@abstractmethod
	def get_observation_hr(self, observation_info):
		"""Returns the observation hr value."""
		pass

	@abstractmethod
	def get_observation_sao2(self, observation_info):
		"""Returns the observation sao2 value."""
		pass

	def get_observation_value(self, observation_info, key):
		"""Returns the requested observation value. If the type is not implemented a warning will be raised."""
		match key:
			case 'fio2':
				return self.get_observation_fio2(observation_info)
			case'pip':
				return self.get_observation_pip(observation_info)
			case 'peep':
				return self.get_observation_peep(observation_info)
			case 'hr':
				return self.get_observation_hr(observation_info)
			case 'sao2':
				return self.get_observation_sao2(observation_info)
			case default:
				warnings.warn('Type: ' + key + ' not implemented.')
				return ''

	@abstractmethod
	def get_observation_unit_string(self, observation_info):
		"""Returns the observation's value unit_string."""
		pass

	@abstractmethod
	def get_observation_system(self):
		"""Returns the system where the observation iformation is stored."""
		pass

	@abstractmethod
	def get_observation_time(self, observation_info):
		"""Returns the time observation was recorded."""
		pass

	def create_observation(self, observation_info, patient_id):
		"""Create a smart Observation object."""
		key = self.KEY_FROM_ITEM_ID[int(self.get_observation_item_id(observation_info))] # raises key error if the item id is not one we have supported
		row_id = self.get_observation_row_id(observation_info)
		value = self.get_observation_value(observation_info, key) # observationInfo.VALUENUM
		unit_string = self.get_observation_unit_string(observation_info) # observation_info.VALUEUOM
		unit_code = self.UNIT_CODE[unit_string]
		loinc = self.LOINC_CODES[key]
		display_string = self.D_ITEMS.loc[self.ITEM_IDS[key]].LABEL
		return Observation({
		  'code' : {
		    'coding' : [
		      {'code': loinc, 'display': display_string, 'system': 'http://loinc.org'}
		    ]
		  },
		  'status' :'final',
		  'subject': {'reference': f'Patient/{patient_id}'},
		  'valueQuantity': {
		    'code': unit_code,
		    'system': 'http://unitsofmeasure.org',
		    'unit': unit_string,
		    'value': value
		  },
		  'identifier' : [
		    {
		      'system' : self.get_observation_system(),
		      'value' : str(row_id),
		    }
		  ],
		  # assume everything is eastern time-- it's all shifted by a century anyway
		  'effectiveDateTime': self.get_observation_time(observation_info).strftime(self.FHIR_DATETIME_FORMAT_STRING),
		})