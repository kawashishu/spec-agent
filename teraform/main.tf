resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.aks_name}-dns"

  default_node_pool {
    name                = "default"
    vm_size             = var.node_size
    node_count          = var.node_count
    enable_auto_scaling = true
    min_count           = var.node_count
    max_count           = 5
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
  }
}

resource "azurerm_role_assignment" "aks_acr" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

resource "azurerm_postgresql_flexible_server" "db" {
  name                   = var.db_name
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  administrator_login    = var.db_admin
  administrator_password = var.db_password
  version                = "14"
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_aks" {
  name             = "allow-aks"
  server_id        = azurerm_postgresql_flexible_server.db.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

resource "kubernetes_secret" "postgres_creds" {
  metadata {
    name = "postgres-creds"
  }
  data = {
    PGHOST     = azurerm_postgresql_flexible_server.db.fqdn
    PGUSER     = var.db_admin
    PGPASSWORD = var.db_password
    PGDATABASE = var.db_name
    PGPORT     = tostring(var.db_port)
  }
  type = "Opaque"
}

resource "kubernetes_deployment" "chatbot" {
  metadata {
    name = "chatbot"
    labels = {
      app = "chatbot"
    }
  }
  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "chatbot"
      }
    }
    template {
      metadata {
        labels = {
          app = "chatbot"
        }
      }
      spec {
        container {
          name  = "chatbot"
          image = "${azurerm_container_registry.acr.login_server}/${var.image_name}"
          port {
            container_port = 8000
          }
          resources {
            limits = {
              cpu    = "2"
              memory = "4Gi"
            }
            requests = {
              cpu    = "1"
              memory = "1Gi"
            }
          }
          env_from {
            secret_ref {
              name = kubernetes_secret.postgres_creds.metadata[0].name
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "chatbot" {
  metadata {
    name = "chatbot-service"
  }
  spec {
    selector = {
      app = kubernetes_deployment.chatbot.metadata[0].labels["app"]
    }
    type = "LoadBalancer"
    port {
      port        = 80
      target_port = 8000
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "chatbot" {
  metadata {
    name = "chatbot-hpa"
  }
  spec {
    min_replicas = 2
    max_replicas = 5
    scale_target_ref {
      kind = "Deployment"
      name = kubernetes_deployment.chatbot.metadata[0].name
      api_version = "apps/v1"
    }
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type               = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}