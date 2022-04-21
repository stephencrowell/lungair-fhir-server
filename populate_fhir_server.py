import numpy as np
import pandas as pd
import os
import names
from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.observation import Observation
from fhirclient.models.bundle import Bundle
from fhirclient.models.bundle import BundleEntry
import json


smart = client.FHIRClient(settings={
  'app_id': 'my_web_app',
  'api_base': f'http://localhost:4004/hapi-fhir-jpaserver/fhir'
})


mimic3_dir = "/home/ebrahim/data/mimic3/MIMIC-III-v1.4/" # TODO make this a command line arg
mimic3_schemas_dir = './mimic3-schemas/'

dtype_string_mapping = { # Map schema dtype string to pandas dtype
  'int4' : "int32_possibly_nan",
  # Why is int4 being treated specially? For easier NaN support; see
  # https://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#support-for-integer-na
  # It just happened to be in these tables that int4 columns were the ones that sometimes had NaNs
  'int2' : np.int16,
  'varchar' : str,
  'numeric' : np.float32,
  'timestamp' : np.datetime64, # pandas handles this differently-- we will deal with the exception below
  'float8' : np.double
}

def get_dtype_dict(pasted_table_path):
  dtype_dict = {}
  with open(pasted_table_path) as f:
    for line in f.readlines():
      column_name, dtype_string = line.split()[:2]
      if dtype_string not in dtype_string_mapping.keys():
        raise KeyError(f"Please add an entry for {dtype_string} to dtype_string_mapping")
      mapped_string = dtype_string_mapping[dtype_string]
      dtype_dict[column_name.upper()] = mapped_string
  return dtype_dict

def read_table(table_name, index_col=None, chunksize=None):
  dtype_dict = get_dtype_dict(os.path.join(mimic3_schemas_dir,f'{table_name}.txt'))
  parse_int = [index_col] # if index col is int, definitely parse it that way b/c it should be NaN anyway

  # It makes sense to also parse all the ID columns as int,
  # however some ID columns in CHARTEVENTS cause trouble, so commenting this out:
  # parse_int += [colname for colname in dtype_dict if '_ID' in colname]

  date_cols = []
  for colname in list(dtype_dict):
    if dtype_dict[colname] == np.datetime64:
      dtype_dict.pop(colname)
      date_cols.append(colname)
      continue
    # We use float in the following for better NaN support, except what we added to parse_int
    if dtype_dict[colname] == "int32_possibly_nan":
      dtype_dict[colname] = np.int32 if colname in parse_int else float

  table_path = os.path.join(mimic3_dir,f'{table_name}.csv.gz')

  # temporary override for faster testing; TODO: remove
  if table_name == 'CHARTEVENTS':
    table_path = './CHARTEVENTS_test.csv'

  return pd.read_csv(
    table_path,
    index_col = index_col,
    dtype=dtype_dict,
    chunksize=chunksize,
    parse_dates = date_cols
  )


ICUSTAYS = read_table('ICUSTAYS', 'ICUSTAY_ID')
NICUSTAYS = ICUSTAYS[ICUSTAYS.FIRST_CAREUNIT == 'NICU']
PATIENTS = read_table('PATIENTS', 'SUBJECT_ID')
NICU_PATIENTS = PATIENTS.loc[NICUSTAYS.SUBJECT_ID.astype(int)]
D_ITEMS = read_table('D_ITEMS', "ITEMID")

nicu_stay_ids = set(NICUSTAYS.index)

with read_table("CHARTEVENTS", index_col="ROW_ID", chunksize=1e6) as reader:
  for n, chunk in enumerate(reader):
    nicu_chartevents_chunk = chunk[chunk.ICUSTAY_ID.isin(nicu_stay_ids)]
    if n==0:
      NICU_CHARTEVENTS = nicu_chartevents_chunk
    else:
      NICU_CHARTEVENTS = pd.concat([NICU_CHARTEVENTS,nicu_chartevents_chunk])
    print(f'chunk {n}/330 done, collected {len(NICU_CHARTEVENTS)} samples in total')

# Pick out the item ID of each chart event that we support exporting to the fhir server
# These IDs were determined by exploring the D_ITEMS table; see https://mimic.mit.edu/docs/iii/tables/d_items/
ITEM_IDS = {
  'fio2' : 3420,
  'pip' : 507,
  'peep' : 505,
  'hr' : 211,
  'sao2' : 834,
}

# Inverse of the ITEM_IDS mapping
KEY_FROM_ITEM_ID = {v:k for k,v in ITEM_IDS.items()}

# LOINC codes that I found these by using loinc.org/search/ ... and making my best guesses when things were unclear
# Not to be fully trusted
LOINC_CODES = {
  'fio2' : '19996-8',
  'pip' : '60951-1',
  'peep' : '20077-4',
  'hr' : '8867-4',
  'sao2' : '59408-5',
}

# Select only the chart events that we support converting into Observation resource
NICU_CHARTEVENTS_SUPPORTED = NICU_CHARTEVENTS[
  NICU_CHARTEVENTS.ITEMID.isin(ITEM_IDS.values()) # ensure that item id is a supported one
  & (NICU_CHARTEVENTS.STOPPED=='NotStopd') # ensure that the measurement was not discontinued
  & (~NICU_CHARTEVENTS.VALUENUM.isna()) # ensure that numerical value is not nan
]

# see https://www.hl7.org/fhir/valueset-administrative-gender.html
FHIR_GENDER_MAPPING = {'M':'male', 'F':'female'}

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
  key = KEY_FROM_ITEM_ID[int(row.ITEMID)] # raises key error if the item id is not one we have supported
  row_id = row.name
  value = row.VALUENUM
  unit_string = row.VALUEUOM
  unit_code = UNIT_CODE[unit_string]
  loinc = LOINC_CODES[key]
  display_string = D_ITEMS.loc[ITEM_IDS[key]].LABEL
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
        'value' : str(row.name),
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


num_chartevents = len(NICU_CHARTEVENTS_SUPPORTED)
num_chartevents_processed = 0

num_patients = len(NICU_PATIENTS)
num_patients_processed = 0

for _,patient_row in NICU_PATIENTS.iterrows():
  patient_chart_events =\
    NICU_CHARTEVENTS_SUPPORTED[NICU_CHARTEVENTS_SUPPORTED.SUBJECT_ID == patient_row.name]
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