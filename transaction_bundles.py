import json
from fhirclient.models.bundle import Bundle
from fhirclient.models.bundle import BundleEntry

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
  res = smart_server.session.post(
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