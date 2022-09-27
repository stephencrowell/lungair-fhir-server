import sys
import argparse
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from transaction_bundles import create_transaction_bundle_object, post_transaction_bundle
from mimic3 import Mimic3

parser = argparse.ArgumentParser()

parser.add_argument('--mimic3_dir', type=str, help='MIMIC3 data directory')
parser.add_argument('--fhir_server', type=str, help='FHIR server')

args = parser.parse_args()


fhir_server_url = args.fhir_server
mimic3_dir = args.mimic3_dir

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

mimic3 = Mimic3()

mimic3.initData(mimic3_dir, './mimic3-schemas/')

num_chartevents = len(mimic3.NICU_CHARTEVENTS_SUPPORTED)
num_chartevents_processed = 0

num_patients = len(mimic3.NICU_PATIENTS)
num_patients_processed = 0

for patient_row in mimic3.get_all_patients():
  patient_resource = mimic3.create_patient(patient_row)
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
  for chart_event_row in mimic3.get_patient_chart_events(patient_row.name):
    observation_resource = mimic3.create_observation(chart_event_row, patient_id)
    observations.append(observation_resource)
    num_chartevents_processed += 1
    if (num_chartevents_processed % 100 == 0):
      percent_chartevents = 100 * num_chartevents_processed/num_chartevents
      percent_patients = 100 * num_patients_processed/num_patients
      print(
        f'processed {num_patients_processed}/{num_patients} = {percent_patients:.2f}% patients.',
        f'processed {num_chartevents_processed}/{num_chartevents} = {percent_chartevents:.2f}% chart events',
        sep=', '
      )

  if len(observations)>0:
    transaction_bundle = create_transaction_bundle_object(observations)
    try:
      transaction_response = post_transaction_bundle(smart.server, transaction_bundle)
    except BaseException as e: # Again, make sure to print error message in the response if there is one
      if hasattr(e, 'response') and hasattr(e.response, 'json') and callable(e.response.json):
        print("Error uploading observation bundle to server, response json:", e.response.json(), file=sys.stderr, sep='\n')
    assert(len(observations) == len(transaction_response['entry'])) # There should be as many responses as resources that went in
  num_patients_processed += 1