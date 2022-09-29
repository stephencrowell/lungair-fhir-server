import sys
import argparse
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from transaction_bundles import create_transaction_bundle_object, post_transaction_bundle
from mimic3 import Mimic3
from RandomData import RandomData

parser = argparse.ArgumentParser()

parser.add_argument('--data_type', type=str, help='Type of data generation to use. Either random or mimic3', required=True)
parser.add_argument('--num_of_patients', type=int, help='Number of patients in random generation', required='random' in sys.argv)
parser.add_argument('--num_of_observations_per_patient', type=int, help='Number of observations per patient in random generation', required='random' in sys.argv)
parser.add_argument('--mimic3_dir', type=str, help='MIMIC3 data directory', required='mimic3' in sys.argv)
parser.add_argument('--fhir_server', type=str, help='FHIR server', required=True)

args = parser.parse_args()


fhir_server_url = args.fhir_server
data_type = args.data_type

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
  data_generator = RandomData()
  data_generator.init_data(num_of_patients, num_of_observations_per_patient)
elif (data_type == 'mimic3'):
  mimic3_dir = args.mimic3_dir
  data_generator = Mimic3()
  data_generator.init_data(mimic3_dir, './mimic3-schemas/')
else:
  print(f"Unknown data generation type: {data_type} ")
  exit()

# num_chartevents = len(mimic3.NICU_CHARTEVENTS_SUPPORTED)
# num_chartevents_processed = 0

# num_patients = len(mimic3.NICU_PATIENTS)
# num_patients_processed = 0

for patient_row in data_generator.get_all_patients():
  patient_resource = data_generator.create_patient(patient_row)
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
  for chart_event_row in data_generator.get_patient_chart_events(patient_row):
    observation_resource = data_generator.create_observation(chart_event_row, patient_id)
    observations.append(observation_resource)
    # num_chartevents_processed += 1
    # if (num_chartevents_processed % 100 == 0):
    #   percent_chartevents = 100 * num_chartevents_processed/num_chartevents
    #   percent_patients = 100 * num_patients_processed/num_patients
    #   print(
    #     f'processed {num_patients_processed}/{num_patients} = {percent_patients:.2f}% patients.',
    #     f'processed {num_chartevents_processed}/{num_chartevents} = {percent_chartevents:.2f}% chart events',
    #     sep=', '
    #   )

  if len(observations)>0:
    transaction_bundle = create_transaction_bundle_object(observations)
    try:
      transaction_response = post_transaction_bundle(smart.server, transaction_bundle)
    except BaseException as e: # Again, make sure to print error message in the response if there is one
      if hasattr(e, 'response') and hasattr(e.response, 'json') and callable(e.response.json):
        print("Error uploading observation bundle to server, response json:", e.response.json(), file=sys.stderr, sep='\n')
    assert(len(observations) == len(transaction_response['entry'])) # There should be as many responses as resources that went in
  # num_patients_processed += 1