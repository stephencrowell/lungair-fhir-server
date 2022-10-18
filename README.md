# lungair-fhir-server

*Under development.*

This repository will contain tools for building a pre populated FHIR R4 server,
intended for the construction of sandbox environments for Electronic Health
Records (EHR). `lungair-fhir-server` creates a [FHIR](https://www.hl7.org/fhir/overview.html) server inside a
docker container you can interact with. The FHIR server contains Patients
and Observations from a user defined data source. Currently,
`lungair-fhir-server` supports `FIO2`, `PIP`, `PEEP`, `Heart Rate`, and
`Sa02` Observation types.

## Initial Setup
1. Install [Docker](https://store.docker.com/search?type=edition&offering=community) (if not already installed)
2. Install [Git](https://git-scm.com/downloads) (if not already installed).
3. Clone this project
    ```sh
    git clone git@github.com:KitwareMedical/lungair-fhir-server.git
    ```
4. Download the [hapi r4 container](https://hub.docker.com/layers/hapi-5/smartonfhir/hapi-5/r4-empty/images/sha256-42d138f85967cbcde9ed4f74d8cd57adf9f0b057e9c45ba6a8e1713d3f9e1cea?context=explore) by the SMART on FHIR team
5. Run the docker container
    ```sh
    docker run -dp 3000:8080 smartonfhir/hapi-5:r4-empty
    ```

## Using lungair-fhir-server

With the initial setup finished, you have a few ways to use
`lungair-fhir-server`.
The project is designed for use for three different levels of users:
1. Users who want to generate a FHIR server using the `MIMIC-III` method
or the random method.
2. Users who have their own set of data they want to create a FHIR server for.
3. Users who have additional Observation types they want to use.

The sections below describe how to use `lungair-fhir-server` for each type of user.


### MIMIC-III and Random Generation
#### MIMIC-III
1. Get access to and download [MIMIC-III](https://physionet.org/content/mimiciii/1.4/)
2. Change the `args` in `data_sources/MIMIC-III.json` to where the MIMIC-III
data is and where the MIMIC-III schema is.
    ```json
    "args":
    {
        "mimic3_data_dir": "path/to/mimic3/data/dir",
        "mimic3_schemas_dir": "path/to/mimic3/schema/dir"
    }
    ```
3. Run populate `populate_fhir_server.py`
    ```sh
    python populate_fhir_server.py --json_file ./data_sources/mimic3.json
    	--fhir_server http://localhost:3000/hapi-fhir-jpaserver/fhir/    
    ```
#### Random
1. Change the `args` in `data_sources/random.json` depending
on how much data to generate
    ```json
    "args":
    {
        "num_of_patients": 10,
        "num_of_observations_per_patient": 50
    }
    ```
2. Run populate `populate_fhir_server.py`
    ```sh
    python populate_fhir_server.py --json_file ./data_sources/random.json
    	--fhir_server http://localhost:3000/hapi-fhir-jpaserver/fhir/    
    ```

### Adding a Custom Data Source
The following steps create a minimal working data source for
`lungair-fhir-server`
1. Create a new python file in `data_sources` for your new data source
2. Inside the new python file, create two implementations of `Observation`
and `PatientDataSource` from `patient_data_source.py`
3. Implement `__init__` for your `PatientDataSouce` implementation.
This method should handle importing your data source into python.
4. Implement `create_patient` and `get_patient_observations` for
your `PatientDataSource` implementation. Read the doc strings in
`patient_data_source.py` for more information.
5. Implement `get_observation_type` and `get_value` for your
`Observation` implementation. Read the doc strings in
`patient_data_source.py` for more information.
6. Create a new JSON file for your new data source. It should follow
the format below.
    ```json
    {
        "args":
        {
            "arg1": "arg1_value",
            "arg2": "arg2_value"
        },
        "class_name": "NewPatientDataSource",
        "module_name": "new_patient_data_source"
    }
    ```
It is important to note the `class_name` is the name of the
`PatientDataSource` implementation and `module_name` is the
name of the python file without the file extension.

While this is a viable way to create a new data source, there is
more customization available. All methods with a default
implementation in `Patient` and `Observation` can be changed
in your implementation of `Patient` and `Observation`. This is
not required for `populate_fhir_server.py` to work; however,
it does allow for the data on the FHIR server to represent the
source more accurately.

#### Adding Custom Observation Types
In cases where your data source has additional observation types
not supported by `lungair-fhir-server`, it is possible to add
your own observation types.

1. Create a JSON object in the format below
    ```json
    "ObservationTypeName":
    {
        "display_string": "observation_display_string",
        "unit_code": "observation_unit_code",
        "loinc_code": "observation_loinc_code"
    }
    ```
2. Add the JSON section to `observation_types.json`

The doc strings in `patient_data_source.py` describes how the
values should be filled. For more information, check the FHIR
[documentation](https://www.hl7.org/fhir/observation.html).


