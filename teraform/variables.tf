variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "spec-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "acr_name" {
  description = "Azure Container Registry name"
  type        = string
  default     = "specacr"
}

variable "aks_name" {
  description = "AKS cluster name"
  type        = string
  default     = "spec-aks"
}

variable "node_count" {
  description = "Initial node count"
  type        = number
  default     = 1
}

variable "node_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D2s_v5" # 2 vCPU, 8GiB
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "chatdb"
}

variable "db_admin" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "chatadmin"
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "db_port" {
  description = "PostgreSQL port"
  type        = number
  default     = 5432
}

variable "image_name" {
  description = "Docker image name"
  type        = string
  default     = "chatbot:v1"
}