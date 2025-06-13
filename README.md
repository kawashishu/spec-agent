## Deploying with Terraform

Alternatively, you can deploy the infrastructure using Terraform located in the
`teraform` directory. The configuration creates an App Service plan with
autoscale enabled, a Linux Web App and a PostgreSQL flexible server. All
resources reside in the `rg_spec` resource group within the `southeastasia`
region.

```bash
cd teraform
terraform init
terraform apply -var "db_password=<your-password>"
```

After `apply` completes Terraform prints the Web App hostname and the database
FQDN.
