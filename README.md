# DDB-KG

This repo contains the code for fetching, processing, and storing
xml files from the [Deutsche Digitale Bibliothek](https://deutsche-digitale-bibliothek.de).

## Environment Variables

Before running any code, make sure you have all
required environment files setup and the included
environment variables defined based on your setup.

In the case of the download and location server, navigate
into the corresponding directory, create a copy of the
.template.env-file, rename it to .env, and fill in the
variable values accordingly.

## Installation

Create a [virtual environment](https://docs.python.org/3/library/venv.html)
by executing the following command:

```bash
python3 -m venv venv
```

To activate the virtual environment, execute:

```bash
source venv/bin/activate
```

Then, install all python libraries, the project relies on using
the package manager [pip](https://pip.pypa.io/en/stable/):

```bash
pip3 install -r requirements.txt
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
