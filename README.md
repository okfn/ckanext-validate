[![Tests](https://github.com/okfn/ckanext-validate/workflows/Tests/badge.svg?branch=main)](https://github.com/okfn/ckanext-validate/actions)

# ckanext-validate

A simple CKAN extension to validate tabular data powered by [frictionless data](https://framework.frictionlessdata.io/).


## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.10            | not tested    |
| 2.11            | yes           |


## Installation

To install ckanext-validate:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/okfn/ckanext-validate.git
    cd ckanext-validate
    pip install -e .
	pip install -r requirements.txt

3. Add `validate` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Config settings

None at present

**TODO:** Document any optional config settings here. For example:

	# The minimum number of hours to wait before re-checking a resource
	# (optional, default: 24).
	ckanext.validate.some_setting = some_default_value


## Developer installation

To install ckanext-validate for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/okfn/ckanext-validate.git
    cd ckanext-validate
    pip install -e .
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
