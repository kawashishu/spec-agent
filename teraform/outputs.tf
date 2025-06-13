output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.db.fqdn
}