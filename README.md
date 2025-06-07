# Spec Agent

Spec Agent provides a small collection of LLM powered agents exposed through a FastAPI backend.  Users authenticate via credentials stored in `authen.yaml` and can chat with agents that retrieve specbook information or analyse BOM data.  The previous Streamlit interface has been removed so you can build a custom frontend using the API.

## Requirements

* **Python** >= **3.11**
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

Start the API server with `uvicorn`:

```bash
cd src
uvicorn spec.api.server:app --reload --port 9000
```

The API exposes a single `/chat` endpoint that streams assistant responses as Server-Sent Events. Build any frontend of your choice that consumes this endpoint.

## Deploying to Azure AKS

The `aks` directory contains Kubernetes manifests and helper scripts to deploy this project on Azure. After installing the Azure CLI and `kubectl`, run:

```bash
cd aks
./deploy_aks.sh
```

The script creates a resource group, an Azure Container Registry, an AKS cluster and deploys the application. To preload your BOM data into the persistent volume, copy your data file using:

```bash
./load_data.sh /path/to/data.parquet
```

Use `kubectl get service chatbot-service` to find the external IP once deployment completes.
