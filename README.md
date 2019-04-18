# Slack lunch bot

This project is deployed on [Googles cloud functions](https://cloud.google.com/functions/docs/).

### How to install the dependencies
Usually we use a package manger called [Pipenv](https://pipenv.readthedocs.io/en/latest/) when we setup our python projects. But cloud functions require you to use virtualenv and
requirement.txt file. 

First you need to set up the virtual environment. 
```bash
python3 -m virtualenv venv
```

Then you need to source the environment. 
```bash
source venv/bin/active
```

After you have sourced your environment you can install necessary dependencies.
This will install all dependencies found in requirements.txt. 
```bash
pip install -r requirements.txt
```

### How to run the cloud function locally