output "web_app_url" {
  value = azurerm_linux_web_app.app.default_hostname
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.db.fqdn
}
