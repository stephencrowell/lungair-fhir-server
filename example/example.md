# Creating a Custom Data Source

In order to help you create a custom data source, we will create an example data source here.
We will go through each step with directions as well as showing how we created the example files here.

## Importing Data into Python

We have some [data](example.csv) we wish to load onto a FHIR server. The data is shown in the format below:

| patient_id | patient_name | date | body_weight_kg |
|---|---|---|---|
| 123 | June Davis | 2022-10-30 | 80.4 |
| 123 | June Davis | 2022-12-31 | 82 |
| 123 | June Davis | 2023-05-01 | 81 |
| 456 | Lawrence Simons | 2022-11-02 | 68 |
| 456 | Lawrence Simons | 2023-01-15 | 66 |
| 789 | Steve Ireland | 2021-02-04 | 77.4 |
| 789 | Steve Ireland | 2021-04-05 | 78.6 |
| 789 | Steve Ireland | 2021-04-12 | 78.8 |
| 789 | Steve Ireland | 2021-09-07 | 79 |

The first step is to create a new python file for the `PatientDataSource`, `Patient`, and `Observation` classes.
We created `example_data_source.py` as follows:

```python
    from collections.abc import Iterable
    from .patient_data_source import PatientDataSource, Patient, Observation
    
    class ExamplePatient(Patient):

    class ExampleObservation(Observation):


    class ExampleDataSource(PatientDataSource):

```

The first method we will implement is the `__init__` method for `ExampleDataSource`. This
is where we will handle bringing [example.csv](example.csv) into python. The code below
is reading [example.csv](example.csv) into `self.data`.

```python
    def __init__(self, csv_file):
        self.data = pd.read_csv(csv_file)
```

You can do more processing of your data here if needed, but for our case we are ready to move onto the next step.

## Implementing `get_all_patients`

For a minimal implementation of a custom data source, `get_all_patients` is a simple method. The code
below shows how to create an Iterable of `ExamplePatient`.

```python
    def get_all_patients(self) -> Iterable[Patient]:
        mask1 = df['patient_id'].duplicated(keep = 'first') # Get first occurance of patient_id
        mask2 = df['patient_id'].duplicated(keep = False) # Mark duplicate patient_ids
        mask = not mask1 or not mask2
        return (ExamplePatient(row) for _, row in self.data.iterrows())
``` 

There is a small issue here: `ExamplePatient` does not have an `__init__` method. The next part
of code we need to implement is `ExamplePatient`.

## Implementing `ExamplePatient`

The only two methods we need to implement for `ExamplePatient` are `__init__` and `get_identifier_value`.

For `__init__`, we need to store the information passed from `get_all_patients`. The code below shows
the `__init__` method for `ExamplePatient`.

```python
    def __init__(self, patient_info):
        self.patient_info = patient_info
```

For `get_identifier_value`, we need to return a string to identify the patient for `get_patient_observations`.
We will use the `patient_id` row since the values are unique.

```python
    def get_indentifier_value(self) -> str:
        return str(self.patient_info['patient_id'])
```

For a minimal implementation of `ExamplePatient`, we will not need to implement any other methods. We will discuss
other methods you can implement later.

## Implementing `get_patient_observations`

The `get_patient_observations` method is a bit more complex. We need to get each observation for a given
patient. Using the `get_identifier_value` method we implemented above, the code below shows how to create
an Iterable of `ExampleObservation`

```python
    def get_patient_observations(self, patient : Patient) -> Iterable[Observation]:
        return (ExampleObservation(row) for _, row in self.data[self.data['patient_id'] = patient.get_indentifier_value()].iterrows())

```

Once again, we will need to implement the `__init__` method for `ExampleObservation`.

## Implementing `ExampleObservation`

To implement `__init__`, all we need to do is store the `row` variable passed from `getpatient_observations`.
The code below show how `ExampleObservation` implements `__init__`

```python
    def __init__(self, observation_info):
        self.observation_info = observation_info

    
```
The next two methods we need to implement are `get_observation_type` and `get_value`.

`get_observation_type` returns one of the supported [observation_types.json](../observation_types.json).
For this example, we only return `bodyweight`.

```python
    def get_observation_type(self) -> str:
        return 'bodyweight'

```

`get_value` returns the value associated with the `observation_type`. The code below is how
`ExampleObservation` implements `get_value`.

```python
    def get_value(self) -> str:
        return self.observation_info['body_weight_kg']
```

These are the last methods we are required to implement; however, there is one last file
we will need to create.

## Create JSON

In order for `populate_fhir_server.py` to recognize `ExampleDataSource`, we need to create
a new JSON file with the proper information. [example.json](example.json).

Note that your implementation of `patient_data_source.py` and JSON file should be in `data_sources/`.
`example_data_source.py` and `example.json` are not since they are example files.

After following these steps, you will be able to run `populate_fhir_server.py` with your JSON file as an arguement.

## Adding Customization

While the steps created a minimal implementation, it is possible to implement more methods.
This will allow you to have more information stored on the FHIR server. Two pieces of
information stored in `example.csv` we did not use are `patient_name` and `date`.

For `patient_name`, we can implement `get_name` in `ExamplePatient`. The code below shows a 
possible implementation.

```python
    def get_name(self) -> tuple[str, str]:
        split_name = self.patient_info['patient_name'].split(' ')
        return tuple(split_name[1], split_name[0])
```

Note the last name goes into the first spot of the tuple.

For `data`, we can implement `get_time` in `ExampleObservation`. The code below shows a
possible implementation.

```python
    def get_time(self) -> str:
        return self.observation_info['date'].strftime('%Y-%m-%d')
```

The docstrings in `patient_data_source.py` should help guide your implementation of the subclasses. If more information is needed on the precise meanings of things, check the FHIR [documentation](https://www.hl7.org/fhir/observation.html).
