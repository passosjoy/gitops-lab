# OKE (Oracle Kubernetes Engine) — recomendado quando há créditos trial
# (até 4.500h compute OKE, 500 GB OCIR). Após o trial, prefira VM A1 Always Free + compose.

data "oci_containerengine_cluster_option" "lab" {
  count             = var.create_oke ? 1 : 0
  cluster_option_id = "all"
}

data "oci_containerengine_node_pool_option" "lab" {
  count               = var.create_oke ? 1 : 0
  node_pool_option_id = "all"
}

locals {
  oke_k8s_version = var.create_oke ? coalesce(
    var.oke_kubernetes_version,
    try(reverse(sort(data.oci_containerengine_cluster_option.lab[0].kubernetes_versions))[0], "v1.31.1")
  ) : null

  # Seleciona imagem de nó compatível com o shape/versão quando não informada.
  oke_node_image_id = var.create_oke ? coalesce(
    var.oke_node_image_id,
    try(element([
      for s in data.oci_containerengine_node_pool_option.lab[0].sources :
      s.image_id if strcontains(lower(s.source_name), "oracle-linux") && !strcontains(lower(s.source_name), "gpu")
    ], 0), data.oci_core_images.ol9.images[0].id)
  ) : null
}

resource "oci_containerengine_cluster" "lab" {
  count              = var.create_oke ? 1 : 0
  compartment_id     = oci_identity_compartment.lab.id
  name               = "${local.name_prefix}-oke"
  kubernetes_version = local.oke_k8s_version
  vcn_id             = oci_core_vcn.lab.id
  type               = "BASIC_CLUSTER" # Enhanced requer custos/quotas adicionais em alguns cenários

  endpoint_config {
    is_public_ip_enabled = true
    subnet_id            = oci_core_subnet.public.id
    nsg_ids              = [oci_core_network_security_group.app.id]
  }

  options {
    service_lb_subnet_ids = [oci_core_subnet.public.id]

    add_ons {
      is_kubernetes_dashboard_enabled = false
      is_tiller_enabled               = false
    }

    kubernetes_network_config {
      pods_cidr     = "10.244.0.0/16"
      services_cidr = "10.96.0.0/16"
    }

    persistent_volume_config {
      freeform_tags = local.common_tags
    }
    service_lb_config {
      freeform_tags = local.common_tags
    }
  }

  freeform_tags = local.common_tags
}

resource "oci_containerengine_node_pool" "lab" {
  count              = var.create_oke ? 1 : 0
  cluster_id         = oci_containerengine_cluster.lab[0].id
  compartment_id     = oci_identity_compartment.lab.id
  name               = "${local.name_prefix}-oke-pool"
  kubernetes_version = local.oke_k8s_version
  node_shape         = var.oke_node_shape

  dynamic "node_shape_config" {
    for_each = strcontains(var.oke_node_shape, "Flex") ? [1] : []
    content {
      ocpus         = var.oke_node_ocpus
      memory_in_gbs = var.oke_node_memory_gbs
    }
  }

  node_config_details {
    size    = var.oke_node_count
    nsg_ids = [oci_core_network_security_group.app.id]

    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
      subnet_id           = oci_core_subnet.app.id
    }

    node_pool_pod_network_option_details {
      cni_type       = "OCI_VCN_IP_NATIVE"
      pod_nsg_ids    = [oci_core_network_security_group.app.id]
      pod_subnet_ids = [oci_core_subnet.app.id]
    }

    freeform_tags = local.common_tags
  }

  node_source_details {
    image_id                = local.oke_node_image_id
    source_type             = "IMAGE"
    boot_volume_size_in_gbs = 50
  }

  ssh_public_key = var.ssh_public_key

  initial_node_labels {
    key   = "managed-by"
    value = "terraform"
  }

  freeform_tags = local.common_tags

  lifecycle {
    ignore_changes = [node_source_details[0].image_id, kubernetes_version]
  }
}
