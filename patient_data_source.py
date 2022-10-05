from abc import ABC, abstractmethod
import names
import warnings
from datetime import datetime
from enum import Enum
from collections.abc import Iterable
from fhirclient.models.patient import Patient as FHIR_Patient
from fhirclient.models.observation import Observation as FHIR_Observation
from fhirclient.models.fhirdate import FHIRDate
from dateutil import parser

class Patient(ABC):
	class Gender(Enum):
		male = 0
		female = 1
		other = 2
		unknown = 3

	@abstractmethod
	def get_gender(self) -> Gender:
		"""Returns the patient's gender. Default implementation return Gender.unkown"""		
		return Gender.unknown

	@abstractmethod
	def get_identifier_value(self) -> str:
		"""Returns a id value for internal FHIR use. The tuple(identifier_system, indentifier_value) must be unique."""
		pass

	@abstractmethod
	def get_dob(self) -> str:
		"""Returns the patient's date of birth."""
		pass

	@abstractmethod
	def get_identifier_system(self) -> str:
		"""Returns the namespace for unique identifier values. The tuple(identifier_system, indentifier_value) must be unique."""
		pass

	def generate_name(self, gender : Gender) -> tuple[str, str]:
		"""Generate a first and last name based on gender."""
		match gender:
			case Patient.Gender.male:
				first_name = names.get_first_name('male')
			case Patient.Gender.female:
				first_name = names.get_first_name('female')
			case default:
				first_name = names.get_first_name()

		return names.get_last_name(), first_name

	def get_name(self) -> tuple[str, str]:
		"""Returns a a tuple of the last and first name of the patient. Default implementation generates names based on gender"""
		return self.generate_name(self.get_gender())

class Observation(ABC):
	class ObservationType(Enum):
		fio2 = 0
		pip = 1
		peep = 2
		hr = 3
		sao2 = 4

	# Units used for ObservationType's valus. Codes that follow the spec in https://ucum.org/ucum.html.
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

	# Human readable strings for the ObservationTypes currently implemented.
	DISPLAY_STRINGS = {
	  ObservationType.fio2 : 'ETT Sx Quality',
	  ObservationType.pip : 'PIP',
	  ObservationType.peep : 'PEEP',
	  ObservationType.hr : 'Heart Rate',
	  ObservationType.sao2 : 'Sa02',
	}

	@abstractmethod
	def get_identifier_value(self) -> str:
		"""Returns a id value for internal FHIR use. The tuple(identifier_system, indentifier_value) must be unique."""
		pass

	@abstractmethod
	def get_observation_type(self) -> ObservationType:
		"""Returns the observation's ObservationType. Used internally for returning other Observation attribues"""
		pass

	@abstractmethod
	def get_identifier_system(self) -> str:
		"""Returns the namespace for unique identifier values. The tuple(identifier_system, indentifier_value) must be unique."""
		pass
	
	def get_unit_string(self) -> str:	
		"""Returns humnan readable units for the Observation's value. Default implementation uses UNIT_CODES"""
		return self.get_unit_code()

	def get_display_string(self) -> str:
		"""Returns a human readable description of the ObservationType."""
		return self.DISPLAY_STRINGS[self.get_observation_type()]

	def get_unit_code(self) -> str:
		"""Returns a computer processable form for the Observation's value. Default implementation uses the UCUM system."""
		return self.UNIT_CODES[self.get_observation_type()]

	def get_loinc_code(self) -> str:
		"""Returns a computer processable form for the ObservationType. Default implementation uses the LOINC_CODES."""
		return self.LOINC_CODES[self.get_observation_type()]

	@abstractmethod
	def get_value(self) -> str:
		"""Returns the Observation's value."""
		pass

	@abstractmethod
	def get_time(self) -> datetime:
		"""Returns the observation's recorded time."""
		pass

class PatientDataSource(ABC):
	"""Abstract class for loading patient data into a smart FHIR server"""
	
	@abstractmethod
	def get_all_patients(self) -> Iterable[Patient]:
		"""Returns a list of all Patients."""
		pass

	@abstractmethod
	def get_patient_observations(self, patient : Patient) -> Iterable[Observation]:
		"""Returns a list of all Observation for one patient."""
		pass

	def create_patient(self, patient: Patient) -> FHIR_Patient :
		"""Create a smart FHIR_Patient object."""
		gender = patient.get_gender().name
		family, given = patient.get_name()
		date = FHIRDate(patient.get_dob().isoformat())
		return FHIR_Patient({
		  'gender' : gender,
		  'identifier' : [
		    {
		      'system' : patient.get_identifier_system(),
		      'value' : patient.get_identifier_value(),
		    }
		  ],
		  'birthDate' : date.isostring,
		  'name' : [{'family':family,'given':[given]}],
		})

	def create_observation(self, observation : Observation, patient_id : str) -> FHIR_Observation : 
		"""Create a smart FHIR_Observation object. patient_id is an ID value of a Patient item currently on the FHIR server"""
		unique_id = observation.get_identifier_value()
		value = observation.get_value()
		unit_string = observation.get_unit_string()
		unit_code = observation.get_unit_code()
		loinc = observation.get_loinc_code()
		display_string = observation.get_display_string()
		system = observation.get_identifier_system()
		date = FHIRDate(observation.get_time().isoformat())
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
		      'system' : system,
		      'value' : unique_id,
		    }
		  ],
		  'effectiveDateTime': date.isostring,
		})