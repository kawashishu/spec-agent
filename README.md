## Deploying with Terraform

Alternatively, you can deploy the entire stack using the Terraform configuration
in the `terraform` directory. It provisions the resource group, Azure Container
Registry, AKS cluster and a PostgreSQL flexible server. Database credentials are
supplied via Terraform variables and automatically stored as a Kubernetes secret
so the application can connect without a persistent volume.

```bash
cd terraform
terraform init
terraform apply -var "db_password=<your-password>"
```

After apply completes, Terraform outputs the AKS cluster name, the container
registry login server and the database FQDN.