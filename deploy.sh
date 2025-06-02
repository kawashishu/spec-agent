#!/usr/bin/env bash
set -e

# ─── USER-EDITABLE VARIABLES ────────────────────────────────────────────────
APP_NAME="aiopt-specbook"
RESOURCE_GROUP="rg_specbook"
LOCATION="eastus2"

PLAN_NAME="plan-specbook"
SKU="B3"                         # B-series = hobby / dev.  Change as needed.

ALLOWED_IP_FILE="allowed_IP.txt" # optional – one IPv4/CIDR per line
ENV_FILE=".env"                  # optional – KEY=VALUE lines
RUNTIME="python:3.11"
STARTUP="./run.sh"
# ────────────────────────────────────────────────────────────────────────────

exists() { az "$1" show "${@:2}" >/dev/null 2>&1; }

echo "▶ resource-group"
exists group -n "$RESOURCE_GROUP" || \
  az group create -n "$RESOURCE_GROUP" -l "$LOCATION" >/dev/null

echo "▶ App Service plan"
exists appservice plan -n "$PLAN_NAME" -g "$RESOURCE_GROUP" || \
  az appservice plan create -n "$PLAN_NAME" -g "$RESOURCE_GROUP" \
      --is-linux --sku "$SKU" >/dev/null

# ─── create/update web-app (system-assigned identity) ─────────────────────
if exists webapp -n "$APP_NAME" -g "$RESOURCE_GROUP"; then
  echo "▶ Web App exists"
else
  echo "▶ Creating Web App"
  az webapp create -n "$APP_NAME" -g "$RESOURCE_GROUP" -p "$PLAN_NAME" \
       --runtime $RUNTIME
fi

# ─── optional .env → App Settings ───────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  echo "▶ Upload .env to App Settings"
  declare -a kv=()
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" == \#* ]] && continue
    kv+=("$k=${v//\"/}")
  done < "$ENV_FILE"
  [[ ${#kv[@]} -gt 0 ]] && \
     az webapp config appsettings set -n "$APP_NAME" -g "$RESOURCE_GROUP" \
        --settings "${kv[@]}" >/dev/null
fi

# ─── optional IP allow-list ────────────────────────────────────────────────
if [[ -f "$ALLOWED_IP_FILE" ]]; then
  echo "▶ IP allow-list"
  PRIORITY=100
  while IFS= read -r IP; do
    [[ -z "$IP" || "$IP" == \#* ]] && continue
    if ! az webapp config access-restriction show \
          -n "$APP_NAME" -g "$RESOURCE_GROUP" | grep -q "$IP"; then
      az webapp config access-restriction add -n "$APP_NAME" -g "$RESOURCE_GROUP" \
        --rule-name "Allow_$IP" --action Allow --ip-address "$IP" \
        --priority $PRIORITY >/dev/null
      PRIORITY=$((PRIORITY+1))
    fi
  done < "$ALLOWED_IP_FILE"
fi

# ─── Set startup command ─────────────────────────────────────────────────
echo "▶ Set startup command"
az webapp config set -n "$APP_NAME" -g "$RESOURCE_GROUP" \
   --startup-file "$STARTUP"

echo "▶ Deploying app source code"
az webapp up --name $APP_NAME --resource-group $RESOURCE_GROUP --runtime $RUNTIME --sku $SKU --location $LOCATION --logs

echo "▶ Restart site"
az webapp restart -n "$APP_NAME" -g "$RESOURCE_GROUP" >/dev/null

echo "✅ Deploy complete →  https://$APP_NAME.azurewebsites.net/"
echo "ℹ️  Follow logs → az webapp log tail -n $APP_NAME -g $RESOURCE_GROUP"

az webapp log tail -n "$APP_NAME" -g "$RESOURCE_GROUP"

# az webapp log tail -n aiopt-specbook -g rg_specbook

# Use to remove the deployment when it running, for a new deployment
# az webapp config appsettings delete   --name aiopt-specbook   --resource-group rg_specbook   --setting-names WEBSITE_RUN_FROM_PACKAGE