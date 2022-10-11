import sys
import argparse
from fhirclient import client
from fhirclient.models.patient import Patient as FHIR_Patient
from fhirclient.models.observation import Observation as FHIR_Observation
from transaction_bundles import create_transaction_bundle_object, post_transaction_bundle
from patient_data_source import Patient, Observation
from mimic3 import Mimic3
from random_data import RandomData

parser = argparse.ArgumentParser()

parser.add_argument('--data_type', type=str, help='Type of data generation to use. Either random or mimic3', required=True)
parser.add_argument('--num_of_patients', type=int, help='Number of patients in random generation', required='random' in sys.argv)
parser.add_argument('--num_of_observations_per_patient', type=int, help='Number of observations per patient in random generation', required='random' in sys.argv)
parser.add_argument('--mimic3_dir', type=str, help='MIMIC3 data directory', required='mimic3' in sys.argv)
parser.add_argument('--fhir_server', type=str, help='FHIR server', required=True)

args = parser.parse_args()

data_type = args.data_type
fhir_server_url = args.fhir_server

smart = client.FHIRClient(settings={
  'app_id': 'my_web_app',
  'api_base': fhir_server_url
})

# Make sure the server is there
try:
  smart.server.request_json('Patient')
except BaseException as e:
  print(f"Trouble reading from the given FHIR server-- does the server exist at {fhir_server_url} ?", file=sys.stderr)
  raise

if (data_type == 'random'):
  num_of_patients = args.num_of_patients
  num_of_observations_per_patient = args.num_of_observations_per_patient
  data_generator = RandomData(num_of_patients, num_of_observations_per_patient)
elif (data_type == 'mimic3'):
  mimic3_dir = args.mimic3_dir
  data_generator = Mimic3(mimic3_dir, './mimic3-schemas/')
else:
  print(f"Unknown data generation type: {data_type} ")
  exit()

for patient in data_generator.get_all_patients():
  patient_resource = data_generator.create_patient(patient)
  try:
    response = patient_resource.create(smart.server)
  except BaseException as e:
    # Make sure to print error message in the response if there is one
    # (We caught BaseException because this could be a FHIRServer related exception or an HTTPError, but either way
    # the FHIRServer adds the response as an attribute to the exception)
    if hasattr(e, 'response') and hasattr(e.response, 'json') and callable(e.response.json):
      print("Error uploading patient {patient_row.name} to server, response json:", e.response.json(), file=sys.stderr, sep='\n')
    raise
  patient_id = response['id'] # get the patient id that was newly assigned by the fhir server
  observations = []
  for observation in data_generator.get_patient_observations(patient):
    observation_resource = data_generator.create_observation(observation, patient_id)
    observations.append(observation_resource)

  if len(observations)>0:
    transaction_bundle = create_transaction_bundle_object(observations)
    try:
      transaction_response = post_transaction_bundle(smart.server, transaction_bundle)
    except BaseException as e: # Again, make sure to print error message in the response if there is one
      if hasattr(e, 'response') and hasattr(e.response, 'json') and callable(e.response.json):
        print("Error uploading observation bundle to server, response json:", e.response.json(), file=sys.stderr, sep='\n')
    assert(len(observations) == len(transaction_response['entry'])) # There should be as many responses as resources that went in