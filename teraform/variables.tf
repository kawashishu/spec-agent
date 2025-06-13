variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "rg_spec"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "southeastasia"
}

variable "app_service_plan_name" {
  description = "App Service plan name"
  type        = string
  default     = "asp-spec"
}

variable "web_app_name" {
  description = "Name of the Web App"
  type        = string
  default     = "specapp"
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
