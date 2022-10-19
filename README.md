# lungair-fhir-server

This repository contains tools for building a prepopulated FHIR R4 server,
intended for the construction of sandbox environments for Electronic Health
Records (EHR). `lungair-fhir-server` creates a [FHIR](https://www.hl7.org/fhir/overview.html) server inside a
docker container that you can interact with. The FHIR server contains Patients
and Observations from a user defined data source. Currently,
a handful of observation types are supported such as heart rate and some mechanical ventilation parameters.
The full list of supported observation types can be found in [observation_types.json](observation_types.json).

## Initial Setup

1. Ensure that [Docker](https://docs.docker.com/get-docker/) and [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) are installed.
2. Clone this project.
    ```sh
    git clone git@github.com:KitwareMedical/lungair-fhir-server.git
    ```
3. Download the empty [hapi r4 container](https://hub.docker.com/layers/hapi-5/smartonfhir/hapi-5/r4-empty/images/sha256-42d138f85967cbcde9ed4f74d8cd57adf9f0b057e9c45ba6a8e1713d3f9e1cea?context=explore) by the SMART on FHIR team.
    ```sh
    docker pull smartonfhir/hapi-5:r4-empty
    ```
4. Run the docker container.
    ```sh
    docker run -dp 3000:8080 smartonfhir/hapi-5:r4-empty
    ```
    The port "3000" may be replaced by your choice of port; just replace appearances of "3000" by your choice in the rest of the instructions.
5. Verify that the server is working by visiting http://localhost:3000/hapi-fhir-jpaserver/fhir/Patient. This should display some json.


## Using lungair-fhir-server

With the initial setup finished, there are two ways to use
`lungair-fhir-server`:
1. Use one of the existing data sources, such as the random data generator used for testing, or the data source that takes NICU data from a downloaded MIMIC-III dataset.
2. Create your own `PatientDataSource` to populate your own custom patient and observation data into a FHIR server.

### Random data

This approach can be used to test basic functionality by populating a FHIR server with random data:

```sh
python populate_fhir_server.py --json_file ./data_sources/random.json
    --fhir_server http://localhost:3000/hapi-fhir-jpaserver/fhir/    
```

The amount of data to generate can be configured in [data_sources/random.json](data_sources/random.json).

### MIMIC-III

This approach uses a downloaded [MIMIC-III](https://physionet.org/content/mimiciii/1.4/) dataset to populate a FHIR server with NICU patients and ventilator observations. Note that the MIMIC-III dataset requires credentialed access on PhysioNet.

1. Get access to and download [MIMIC-III](https://physionet.org/content/mimiciii/1.4/).
2. Configure [data_sources/MIMIC-III.json](data_sources/MIMIC-III.json) to point to the location of your downloaded data and the MIMIC-III schema files:
    ```json
    "args":
    {
        "mimic3_data_dir": "path/to/mimic3/data/dir",
        "mimic3_schemas_dir": "path/to/mimic3/schema/dir"
    }
    ```
    The schema files are provided in this repository [here](mimic3-schemas).
3. Run `populate_fhir_server.py`:
    ```sh
    python populate_fhir_server.py --json_file ./data_sources/mimic3.json
    	--fhir_server http://localhost:3000/hapi-fhir-jpaserver/fhir/    
    ```


### Custom data source

To populate the FHIR server with your own data, you will need to write a bit of python.
The procedure is to subclass the `PatientDataSource`, `Patient`, and `Observation` classes in [data_sources/patient_data_source.py](data_sources/patient_data_source.py), specifying how the patient and observation data should be created.

The following steps create a minimal working data source:
1. Create a new python file in for your new data source, importing `PatientDataSource`, `Patient`, and `Observation` from [data_sources/patient_data_source.py](data_sources/patient_data_source.py).
2. Inside the new python file, create two implementations of `Observation`
and `PatientDataSource` from `patient_data_source.py`.
3. Implement `__init__` for your `PatientDataSouce` implementation
This method should handle importing your data source into python.
4. Implement `create_patient` and `get_patient_observations` for
your `PatientDataSource` implementation. Read the doc strings in
`patient_data_source.py` for more information.
5. Implement `get_observation_type` and `get_value` for your
`Observation` implementation. Read the doc strings in
`patient_data_source.py` for more information.
6. Create a new JSON file for your new data source. It should follow
the format below
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
Note that `class_name` is the name of the
`PatientDataSource` implementation and `module_name` is the
name of the python file without the file extension.

The docstrings in `patient_data_source.py` should help guide your implementation of the subclasses. If more information is needed on the precise meanings of things, check the FHIR [documentation](https://www.hl7.org/fhir/observation.html).

While this is a viable way to create a new data source, there is
more customization available. All methods with a default
implementation in `Patient` and `Observation` can be changed
in your implementation of `Patient` and `Observation`. This is
not required for `populate_fhir_server.py` to work; however,
it does allow for the data on the FHIR server to represent the
source more accurately.

#### Adding Custom Observation Types

In cases where your data source has additional observation types
not supported in [observation_types.json](observation_types.json), it is possible to add
your own observation types by simply adding an entry to [observation_types.json](observation_types.json):

```json
"ObservationTypeName":
{
    "display_string": "...",
    "unit_code": "...",
    "loinc_code": "..."
}
```
- The `display_string` is a a human readable description of the observation type, e.g. "heart rate".
- The `unit_code` describes the observation's unit of measure in the format of the [UCUM system](http://unitsofmeasure.org)
- The `loinc_code` is a [LOINC code](https://en.wikipedia.org/wiki/LOINC) identifying the observation type. You can search for LOINC codes [here](https://loinc.org/search/).

