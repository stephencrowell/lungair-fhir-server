import json
with open('args.json') as json_file:
  json_dict = json.load(json_file)
  for data_source in json_dict:
  	exec('from .{0} import {1}'.format(data_source, json_dict[data_source]['import_name']))