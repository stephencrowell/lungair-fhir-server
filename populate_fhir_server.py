import sys
import argparse
import json
from fhirclient import client
from transaction_bundles import create_transaction_bundle_object, post_transaction_bundle
from data_sources import *

parser = argparse.ArgumentParser()
parser.add_argument('--data_type', type=str, help='Type of data generation to use', required=True)
parser.add_argument('--fhir_server', type=str, help='FHIR server', required=True)

with open('args.json') as json_file:
  json_dict = json.load(json_file)
  for data_source in json_dict:
    for data_source_args in json_dict[data_source]['args']:
      parser.add_argument('--{0}'.format(data_source_args['name']), type=eval(data_source_args['type']),
        help=data_source_args['help'], required=data_source_args['name'] in sys.argv)


  args = parser.parse_args()
  if (args.data_type in json_dict.keys()):
    klass = globals()[json_dict[args.data_type]['import_name']]
    arg_string = ''
    for data_source_args in json_dict[args.data_type]['args']:
      arg_string = arg_string + 'args.{0}'.format(data_source_args['name'])
    print(arg_string)
    data_generator = eval('klass({0})'.format(arg_string))
  else:
    print(f"Unknown data generation type: {args.data_type} ")
    exit()
  


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