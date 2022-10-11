from abc import ABC, abstractmethod
import names
import warnings
from enum import Enum
from collections.abc import Iterable
from fhirclient.models.patient import Patient as FHIR_Patient
from fhirclient.models.observation import Observation as FHIR_Observation
from fhirclient.models.fhirdate import FHIRDate

class Patient(ABC):
	"""Abstract class for storing Patient data"""
	class Gender(Enum):
		MALE = 0
		FEMALE = 1
		OTHER = 2
		UNKNOWN = 3

	def get_gender(self) -> Gender:
		"""Returns the patient's gender. Default implementation returns Gender.UNKNOWN"""		
		return Patient.Gender.UNKNOWN

	def get_identifier_value(self) -> str:
		"""Return a custom identifier for the Patient. This is not the ID that will be used internally by the server.
		This could be used to link the Patient to its point of origin in the data source, for example. Implementation
		is not requried."""
		return None

	def get_dob(self) -> str:
		"""Returns the patient's date of birth. FHIR supported formats are YYYY, YYYY-MM, YYYY-MM-DD, or
		YYYY-MM-DDThh:mm:ss+zz:zz as described https://build.fhir.org/datatypes.html#dateTime. Implementation is not required"""
		return None

	def get_identifier_system(self) -> str:
		"""Returns a description of the way to interpret the custom identifiers returned by get_identifier_value.
		Implementation is not requried."""
		return None

	def generate_name(self, gender : Gender) -> tuple[str, str]:
		"""Generate a tuple(last name, first name) based on gender."""
		if(gender == Patient.Gender.MALE):
			first_name = names.get_first_name('male')
		elif(gender == Patient.Gender.FEMALE):
			first_name = names.get_first_name('female')
		else:
			first_name = names.get_first_name()

		return names.get_last_name(), first_name

	def get_name(self) -> tuple[str, str]:
		"""Returns the tuple(last name, first name) for the patients name. Default implementation generates names based on gender"""
		return self.generate_name(self.get_gender())

class Observation(ABC):
	"""Abstract class for storing Observation data"""
	class ObservationType(Enum):
		FIO2 = 0
		PIP = 1
		PEEP = 2
		HR = 3
		SAO2 = 4

	# Units used for ObservationType's valus. Codes that follow the spec in https://ucum.org/ucum.html.
	UNIT_CODES = {
	  ObservationType.FIO2 : '',
	  ObservationType.PIP : 'cm[H20]',
	  ObservationType.PEEP : 'cm[H20]',
	  ObservationType.HR : '/min',
	  ObservationType.SAO2 : '%',
	}

	# LOINC codes that I found by using loinc.org/search/ ... and making my best guesses when things were unclear
	# Not to be fully trusted
	LOINC_CODES = {
	  ObservationType.FIO2 : '19996-8',
	  ObservationType.PIP : '60951-1',
	  ObservationType.PEEP : '20077-4',
	  ObservationType.HR : '8867-4',
	  ObservationType.SAO2 : '59408-5',
	}

	# Human readable strings for the ObservationTypes currently implemented.
	DISPLAY_STRINGS = {
	  ObservationType.FIO2 : 'ETT Sx Quality',
	  ObservationType.PIP : 'PIP',
	  ObservationType.PEEP : 'PEEP',
	  ObservationType.HR : 'Heart Rate',
	  ObservationType.SAO2 : 'Sa02',
	}

	def get_identifier_value(self) -> str:
		"""Return a custom identifier for the Observation. This is not the ID that will be used internally by the server.
		This could be used to link the Observation to its point of origin in the data source, for example. Implementation
		is not required."""
		return None

	@abstractmethod
	def get_observation_type(self) -> ObservationType:
		"""Returns the observation's ObservationType. Used internally for returning other Observation attribues."""
		pass

	def get_identifier_system(self) -> str:
		"""Returns a description of the way to interpret the custom identifiers returned by get_identifier_value.
		Implementation is not required."""
		return None
	
	def get_unit_string(self) -> str:	
		"""Returns humnan readable units for the Observation's value. Default implementation uses UNIT_CODES"""
		return self.get_unit_code()

	def get_display_string(self) -> str:
		"""Returns a human readable description of the ObservationType."""
		return self.DISPLAY_STRINGS[self.get_observation_type()]

	def get_unit_code(self) -> str:
		"""Returns a computer processable form for the Observation's value. Default implementation uses the UCUM system."""
		return self.UNIT_CODES[self.get_observation_type()]

	def get_observation_code_value(self) -> str:
		"""Returns a computer processable form for the ObservationType. Default implementation uses the LOINC codes."""
		return self.LOINC_CODES[self.get_observation_type()]

	def get_observation_code_system(self) -> str:
		"""Returns the coding system used by get_observation_code_value. Default implementation is LOINC codes"""
		return 'http://loinc.org'

	@abstractmethod
	def get_value(self) -> str:
		"""Returns the Observation's value."""
		pass

	def get_time(self) -> str:
		"""Returns the observation's recorded time. FHIR supported formats are YYYY, YYYY-MM, YYYY-MM-DD, or
		YYYY-MM-DDThh:mm:ss+zz:zz as described https://build.fhir.org/datatypes.html#dateTime. Implementation is not required."""
		return None

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
		gender = patient.get_gender().name.lower()
		family, given = patient.get_name()
		date = patient.get_dob()

		fhir_patient_args = {
		  'gender' : gender,
		  'name' : [{'family':family,'given':[given]}],
		}

		if (date is not None):
			fhir_patient_args['birthDate'] = date

		identifier_system = patient.get_identifier_system()
		identifier_value = patient.get_identifier_value()

		if (identifier_system is not None and identifier_value is not None):
			fhir_patient_args['identifier'] = [{
				'system': identifier_system,
				'value': identifier_value
			}]
		elif (identifier_system is not None):
			fhir_patient_args['identifier'] = [{
				'system': identifier_system
			}]
		elif (identifier_value is not None):
			fhir_patient_args['identifier'] = [{
				'value': identifier_value
			}]

		return FHIR_Patient(fhir_patient_args)

	def create_observation(self, observation : Observation, patient_id : str) -> FHIR_Observation : 
		"""Create a smart FHIR_Observation object. patient_id is an ID value of a Patient item currently on the FHIR server"""
		value = observation.get_value()
		unit_string = observation.get_unit_string()
		unit_code = observation.get_unit_code()
		code_value = observation.get_observation_code_value()
		code_system = observation.get_observation_code_system()
		display_string = observation.get_display_string()
		date = observation.get_time()

		fhir_observation_args = {
		  'code' : {
		    'coding' : [
		      {'code': code_value, 'display': display_string, 'system': code_system}
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
		}

		if (date is not None):
			fhir_observation_args['effectiveDateTime'] = date

		identifier_system = observation.get_identifier_system()
		identifier_value = observation.get_identifier_value()

		if (identifier_system is not None and identifier_value is not None):
			fhir_observation_args['identifier'] = [{
				'system': identifier_system,
				'value': identifier_value
			}]
		elif (identifier_system is not None):
			fhir_observation_args['identifier'] = [{
				'system': identifier_system
			}]
		elif (identifier_value is not None):
			fhir_observation_args['identifier'] = [{
				'value': identifier_value
			}]

		return FHIR_Observation(fhir_observation_args)