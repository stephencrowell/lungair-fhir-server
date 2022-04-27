import names
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from fhirclient.models.bundle import Bundle
from fhirclient.models.bundle import BundleEntry
import json
from mimic3 import Mimic3


smart = client.FHIRClient(settings={
  'app_id': 'my_web_app',
  'api_base': f'http://localhost:4004/hapi-fhir-jpaserver/fhir'
})


mimic3_dir = "/home/ebrahim/data/mimic3/MIMIC-III-v1.4/" # TODO make this a command line arg
mimic3_schemas_dir = './mimic3-schemas/'

mimic3 = Mimic3(mimic3_dir, mimic3_schemas_dir)

# see https://www.hl7.org/fhir/valueset-administrative-gender.html
FHIR_GENDER_MAPPING = {'M':'male', 'F':'female'}

# LOINC codes that I found by using loinc.org/search/ ... and making my best guesses when things were unclear
# Not to be fully trusted
LOINC_CODES = {
  'fio2' : '19996-8',
  'pip' : '60951-1',
  'peep' : '20077-4',
  'hr' : '8867-4',
  'sao2' : '59408-5',
}

def generate_name(gender):
  return names.get_last_name(), names.get_first_name('male' if gender=='M' else 'female')

def create_patient_from_row(row):
  """Create a smart Patient object using a row from the MIMIC-III PATIENTS table.
  They are assigned a randomly generated name, just for some flavor.
  Their mimic subject ID is preserved as an 'identifier'."""
  family, given = generate_name(row.GENDER)
  return Patient({
    'gender' : FHIR_GENDER_MAPPING[row.GENDER],
    'identifier' : [
      {
        'system' : 'https://mimic.mit.edu/docs/iii/tables/patients/#subject_id',
        'value' : str(row.name),
      }
    ],
    'birthDate' : row.DOB.strftime('%Y-%m-%d'),
    'name' : [{'family':family,'given':[given]}],
  })

# Map unit strings from the VALUEUOM column of CHARTEVETS to codes that follow the spec in
# https://ucum.org/ucum.html
UNIT_CODE = {
  'bpm':'/min',
  'cmH20':'cm[H2O]',
  '%':'%',
}

# see http://hl7.org/fhir/R4/datatypes.html#dateTime
# and https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
FHIR_DATETIME_FORMAT_STRING = '%Y-%m-%dT%H:%M:%S-05:00'

def create_observation_from_row(row, patient_id):
  """Given a row from the MIMIC-III CHARTEVENTS table, see if the ITEMID is one
  of the supported types and create an Observation from it."""
  key = mimic3.KEY_FROM_ITEM_ID[int(row.ITEMID)] # raises key error if the item id is not one we have supported
  row_id = row.name
  value = row.VALUENUM
  unit_string = row.VALUEUOM
  unit_code = UNIT_CODE[unit_string]
  loinc = LOINC_CODES[key]
  display_string = mimic3.D_ITEMS.loc[mimic3.ITEM_IDS[key]].LABEL
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
        'system' : 'ROW_ID in https://mimic.mit.edu/docs/iii/tables/chartevents/',
        'value' : str(row_id),
      }
    ],
    # assume everything is eastern time-- it's all shifted by a century anyway
    'effectiveDateTime': row.CHARTTIME.strftime(FHIR_DATETIME_FORMAT_STRING),
  })


post_bundle_headers = {
  'Content-type': 'application/fhir+json',
  'Accept': 'application/fhir+json',
  'Accept-Charset': 'UTF-8',
}

def post_transaction_bundle(smart_server, bundle):
  """ Calling the create method on a bundle of type transaction does not work in the smart api.
  This is because the url to send the post request to should be the base url
  (see https://stackoverflow.com/a/62884954/5329413)
  but smart fhir server is designed to always add '/Bundle/'
  (see https://github.com/smart-on-fhir/client-py/blob/6047277daa31f10931e44ed19e92128298cdb64b/fhirclient/server.py#L232)"""
  res = smart.server.session.post(
    smart_server.base_uri,
    headers=post_bundle_headers,
    data=json.dumps(bundle.as_json())
  )
  if res.status_code < 400:
    return res.json()
  else:
    raise Exception(f"FHIR error {res.status_code}; response json:\n"+str(res.json()))

def create_transaction_bundle_object(resources):
  """Given a list of resources, return a Bundle of transaction type"""
  b = Bundle({
    'type':'transaction',
    'entry' : [],
  })
  for resource in resources:
    b.entry.append(BundleEntry({
      "resource" : resource.as_json(),
      # https://build.fhir.org/bundle-definitions.html#Bundle.entry.request.method
      'request' : {'method' : "POST", 'url' : resource.relativeBase()}
    }))
  return b


num_chartevents = len(mimic3.NICU_CHARTEVENTS_SUPPORTED)
num_chartevents_processed = 0

num_patients = len(mimic3.NICU_PATIENTS)
num_patients_processed = 0

for _,patient_row in mimic3.NICU_PATIENTS.iterrows():
  patient_chart_events =\
    mimic3.NICU_CHARTEVENTS_SUPPORTED[mimic3.NICU_CHARTEVENTS_SUPPORTED.SUBJECT_ID == patient_row.name]
  patient_resource = create_patient_from_row(patient_row)
  response = patient_resource.create(smart.server)
  patient_id = response['id'] # get the patient id that was newly assigned by the fhir server
  observations = []
  for _,chart_event_row in patient_chart_events.iterrows():
    observation_resource = create_observation_from_row(chart_event_row, patient_id)
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
    transaction_response = post_transaction_bundle(smart.server, transaction_bundle)
    assert(len(observations) == len(transaction_response['entry'])) # make sure there are as many responses as resources that went in

  num_patients_processed += 1

  # TODO: temporary measure for faster testing, remove this
  if num_patients_processed > 100: break