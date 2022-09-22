from abc import ABC, abstractmethod

class AbstractLungairData(ABC):
	"""Abstract class for loading patient data into a smart FHIR server"""
	def __init__(self):
		pass

	def getAllPatients(self):
		"""Returns a list of all patients."""
		pass

	def getPatientChartEvent(self, patientName):
		"""Returns a list of all Chart Events for one patient."""
		pass

	def createPatient(self, patientInfo):
		"""Create a smart Patient object."""
		pass

	def createObservation(self, observationInfo, patient_id):
		"""Create a smart Observation object."""
		pass