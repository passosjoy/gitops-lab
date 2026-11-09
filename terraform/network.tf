data "oci_core_services" "all" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

resource "oci_core_vcn" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  display_name   = "${local.name_prefix}-vcn"
  cidr_blocks    = [var.vcn_cidr]
  dns_label      = "labvcn"

  freeform_tags = local.common_tags
}

resource "oci_core_internet_gateway" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-igw"
  enabled        = true

  freeform_tags = local.common_tags
}

resource "oci_core_nat_gateway" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-nat"

  freeform_tags = local.common_tags
}

resource "oci_core_service_gateway" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-sgw"

  services {
    service_id = data.oci_core_services.all.services[0].id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-rt-public"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.lab.id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_route_table" "app" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-rt-app"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.lab.id
  }

  route_rules {
    destination       = data.oci_core_services.all.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.lab.id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_route_table" "db" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-rt-db"

  route_rules {
    destination       = data.oci_core_services.all.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.lab.id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_subnet" "public" {
  compartment_id             = oci_identity_compartment.lab.id
  vcn_id                     = oci_core_vcn.lab.id
  display_name               = "${local.name_prefix}-subnet-public"
  cidr_block                 = var.public_subnet_cidr
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.public.id
  prohibit_public_ip_on_vnic = false

  freeform_tags = local.common_tags
}

resource "oci_core_subnet" "app" {
  compartment_id             = oci_identity_compartment.lab.id
  vcn_id                     = oci_core_vcn.lab.id
  display_name               = "${local.name_prefix}-subnet-app"
  cidr_block                 = var.app_subnet_cidr
  dns_label                  = "app"
  route_table_id             = oci_core_route_table.app.id
  prohibit_public_ip_on_vnic = true

  freeform_tags = local.common_tags
}

resource "oci_core_subnet" "db" {
  compartment_id             = oci_identity_compartment.lab.id
  vcn_id                     = oci_core_vcn.lab.id
  display_name               = "${local.name_prefix}-subnet-db"
  cidr_block                 = var.db_subnet_cidr
  dns_label                  = "db"
  route_table_id             = oci_core_route_table.db.id
  prohibit_public_ip_on_vnic = true

  freeform_tags = local.common_tags
}

resource "oci_core_network_security_group" "app" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-nsg-app"

  freeform_tags = local.common_tags
}

resource "oci_core_network_security_group" "db" {
  compartment_id = oci_identity_compartment.lab.id
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${local.name_prefix}-nsg-db"

  freeform_tags = local.common_tags
}

resource "oci_core_network_security_group_security_rule" "app_ingress_ssh" {
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.assign_public_ip ? var.admin_cidr : var.vcn_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH admin (restrinja admin_cidr ao seu IP/32)"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "app_ingress_http" {
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  description               = "HTTP/ingress lab"

  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}

resource "oci_core_network_security_group_security_rule" "app_ingress_https" {
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_network_security_group_security_rule" "app_ingress_app" {
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  description               = "App/NodePort direto (lab)"

  tcp_options {
    destination_port_range {
      min = 5000
      max = 5000
    }
  }
}

resource "oci_core_network_security_group_security_rule" "app_ingress_k3s_api" {
  count                     = var.bootstrap_k3s ? 1 : 0
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.admin_cidr
  source_type               = "CIDR_BLOCK"
  description               = "k3s API (kubectl remoto) — restrinja admin_cidr"

  tcp_options {
    destination_port_range {
      min = 6443
      max = 6443
    }
  }
}

resource "oci_core_network_security_group_security_rule" "app_egress_all" {
  network_security_group_id = oci_core_network_security_group.app.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}

resource "oci_core_network_security_group_security_rule" "db_ingress_sql" {
  network_security_group_id = oci_core_network_security_group.db.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.app_subnet_cidr
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 1521
      max = 1522
    }
  }
}

resource "oci_core_network_security_group_security_rule" "db_egress_all" {
  network_security_group_id = oci_core_network_security_group.db.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}

resource "oci_logging_log_group" "lab" {
  count          = var.enable_flow_logs ? 1 : 0
  compartment_id = oci_identity_compartment.lab.id
  display_name   = "${local.name_prefix}-logs"

  freeform_tags = local.common_tags
}

resource "oci_logging_log" "vcn_flow" {
  count        = var.enable_flow_logs ? 1 : 0
  display_name = "${local.name_prefix}-vcn-flow"
  log_group_id = oci_logging_log_group.lab[0].id
  log_type     = "SERVICE"
  is_enabled   = true

  configuration {
    source {
      category    = "all"
      resource    = oci_core_vcn.lab.id
      service     = "flowlogs"
      source_type = "OCISERVICE"
    }
  }

  freeform_tags = local.common_tags
}
