from abc import ABC, abstractmethod
import names
import warnings
from datetime import datetime
from enum import Enum
from fhirclient.models.patient import Patient as FHIR_Patient
from fhirclient.models.observation import Observation as FHIR_Observation

class Patient(ABC):

	@abstractmethod
	def get_gender(self) -> str:
		"""Returns the patient's gender."""		
		pass

	@abstractmethod
	def get_id(self) -> str:
		"""Returns the patient's id."""
		pass

	@abstractmethod
	def get_dob(self) -> datetime:
		"""Returns the patient's DOB."""
		pass

	def generate_name(self, gender):
		"""Returns a first and last name based on gender."""
		return names.get_last_name(), names.get_first_name('male' if gender=='M' else 'female')

	def get_name(self):
		return self.generate_name(self.get_gender())

class Observation(ABC):
	class ObservationType(Enum):
		fio2 = 0
		pip = 1
		peep = 2
		hr = 3
		sao2 = 4

	# Map unit strings from the VALUEUOM column of CHARTEVETS to codes that follow the spec in
    # https://ucum.org/ucum.html
	UNIT_CODES = {
	  ObservationType.fio2 : '',
	  ObservationType.pip : 'cm[H20]',
	  ObservationType.peep : 'cm[H20]',
	  ObservationType.hr : '/min',
	  ObservationType.sao2 : '%',
	}

	# LOINC codes that I found by using loinc.org/search/ ... and making my best guesses when things were unclear
	# Not to be fully trusted
	LOINC_CODES = {
	  ObservationType.fio2 : '19996-8',
	  ObservationType.pip : '60951-1',
	  ObservationType.peep : '20077-4',
	  ObservationType.hr : '8867-4',
	  ObservationType.sao2 : '59408-5',
	}

	DISPLAY_STRINGS = {
	  ObservationType.fio2 : 'ETT Sx Quality',
	  ObservationType.pip : 'PIP',
	  ObservationType.peep : 'PEEP',
	  ObservationType.hr : 'Heart Rate',
	  ObservationType.sao2 : 'Sa02',
	}

	@abstractmethod
	def get_id(self) -> str:
		"""Returns the observation's id."""
		pass

	@abstractmethod
	def get_observation_type(self) -> ObservationType:
		pass
	
	def get_unit_string(self) -> str:
		return self.UNIT_CODE[self.get_observation_type()]

	def get_display_string(self) -> str:
		return self.DISPLAY_STRINGS[self.get_observation_type()]

	def get_unit_code(self) -> str:
		return self.UNIT_CODE[self.get_observation_type()]

	def get_loinc_code(self) -> str:
		return self.LOINC_CODES[self.get_observation_type()]

	@abstractmethod
	def get_value(self) -> str:
		pass

	@abstractmethod
	def get_time(self) -> datetime:
		"""Returns the patient's name."""
		pass

class PatientDataSource(ABC):
	"""Abstract class for loading patient data into a smart FHIR server"""
	
	@abstractmethod
	def get_all_patients(self):
		"""Returns a list of all Patients."""
		pass

	@abstractmethod
	def get_patient_observations(self, patient : Patient):
		"""Returns a list of all Observation for one patient."""
		pass

	@abstractmethod
	def get_patient_system(self):
		"""Returns the system where the patient information is stored."""		
		pass

	def create_patient(self, patient: Patient) -> FHIR_Patient :
		"""Create a smart FHIR_Patient object."""
		gender = patient.get_gender()
		family, given = patient.get_name()
		return FHIR_Patient({
		  'gender' : gender,
		  'identifier' : [
		    {
		      'system' : self.get_patient_system(),
		      'value' : patient.get_id(),
		    }
		  ],
		  'birthDate' : patient.get_dob().strftime('%Y-%m-%d'),
		  'name' : [{'family':family,'given':[given]}],
		})

	@abstractmethod
	def get_observation_system(self):
		"""Returns the system where the observation iformation is stored."""
		pass

	def create_observation(self, observation: Observation, patient_id) -> FHIR_Observation : 
		"""Create a smart FHIR_Observation object."""
		key = observation.get_observation_type().name # raises key error if the item id is not one we have supported
		row_id = observation.get_id()
		value = observation.get_value()
		unit_string = observation.get_unit_string()
		unit_code = observation.get_unit_string()
		loinc = observation.get_loinc_code()
		display_string = observation.get_display_string()
		return FHIR_Observation({
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
		      'value' : row_id,
		    }
		  ],
		  # assume everything is eastern time-- it's all shifted by a century anyway
		  'effectiveDateTime': observation.get_time().strftime('%Y-%m-%dT%H:%M:%S-05:00'),
		})