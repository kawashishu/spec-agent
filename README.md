# Spec Agent

Spec Agent provides a small collection of LLM powered agents exposed through a FastAPI backend and a Streamlit web UI.  Users authenticate via credentials stored in `authen.yaml` and can chat with agents that retrieve specbook information or analyse BOM data.

## Requirements

* **Python** &ge; **3.11**
* Recommended: create a virtual environment before installing packages.

Install dependencies with either:

```bash
pip install -r requirements.txt          # basic install
# or
pip install -e .                          # use pyproject.toml
```

## Environment variables

The application relies on several environment variables. These can be set in your shell or via a `.env` file which is loaded automatically.

Required variables:

- `ACCESS_KEY_ID` – AWS access key for S3 operations
- `SECRET_ACCESS_KEY` – AWS secret key for S3

Optional variables:      

- `PORT` – port for the FastAPI server (defaults to `9000`)
- `URL` – base URL used by the Streamlit UI to talk to the API (defaults to `http://localhost:$PORT`)

Create `authen.yaml` in the project root containing user login information. A helper script `src/spec/utils/authengen.py` can generate a file with hashed passwords.

## Running the application

The easiest way to run both the API and the UI locally is with the provided script:

```bash
./run.sh
```

This launches the FastAPI backend (`python -m spec.api.server`) and the Streamlit UI on port `8000`. With the default settings the backend listens on `http://localhost:9000`.

You may also start the services manually:

```bash
cd src
python -m spec.api.server               # backend on port 9000
streamlit run spec.ui.app --server.port 8000 --server.address 0.0.0.0
```

Once running, navigate to `http://localhost:8000` and log in with one of the accounts defined in `authen.yaml` to start chatting with the agents.