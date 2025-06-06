#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd); cd "$SCRIPT_DIR"

# ------------------- CONFIGURABLE VARIABLES -------------------
RESOURCE_GROUP="spec-rg"
LOCATION="eastus"
ACR_NAME="specacr"
AKS_NAME="spec-aks"
IMAGE_NAME="chatbot:v1"
NODE_COUNT=2
NODE_SIZE="Standard_DS4_v2"

# --------------------------------------------------------------

if ! az account show >/dev/null 2>&1; then
  echo "Please login using 'az login'" >&2
  exit 1
fi

# create resource group
az group create -n "$RESOURCE_GROUP" -l "$LOCATION" >/dev/null

# create container registry if it does not exist
if ! az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az acr create -n "$ACR_NAME" -g "$RESOURCE_GROUP" --sku Basic >/dev/null
fi
ACR_LOGIN=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query "loginServer" -o tsv)

# build and push image
az acr build -r "$ACR_NAME" -t "$IMAGE_NAME" ..

# create AKS cluster if needed
if ! az aks show -n "$AKS_NAME" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az aks create -g "$RESOURCE_GROUP" -n "$AKS_NAME" \
    --node-count "$NODE_COUNT" --node-vm-size "$NODE_SIZE" \
    --attach-acr "$ACR_NAME" --generate-ssh-keys >/dev/null
fi

# get kubeconfig
az aks get-credentials -g "$RESOURCE_GROUP" -n "$AKS_NAME"

# deploy manifests
kubectl apply -f data-pvc.yaml
sed "s|REPLACE_IMAGE|$ACR_LOGIN/$IMAGE_NAME|" chatbot-deployment.yaml | kubectl apply -f -
kubectl apply -f chatbot-service.yaml
kubectl apply -f chatbot-hpa.yaml

echo "Deployment complete. Use 'kubectl get service chatbot-service' for the external IP."
