#!/usr/bin/env bash
set -euo pipefail

# Assumes AKS credentials are already configured and image exists in ACR
DATA_FILE=${1:-data.parquet}
IMAGE_NAME="chatbot:v1"
ACR_NAME="specacr"

ACR_LOGIN=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)

kubectl run data-loader --image=$ACR_LOGIN/$IMAGE_NAME --restart=Never --overrides='{
  "spec": {
    "containers": [{
      "name": "data-loader",
      "image": "'$ACR_LOGIN/$IMAGE_NAME'",
      "command": ["/bin/bash", "-c", "--"],
      "args": ["sleep 3600"],
      "volumeMounts": [{"name": "data-volume", "mountPath": "/mnt/data"}]
    }],
    "volumes": [{"name": "data-volume", "persistentVolumeClaim": {"claimName": "data-pvc"}}]
  }
}'

kubectl cp "$DATA_FILE" data-loader:/mnt/data/$(basename "$DATA_FILE")

kubectl delete pod data-loader
