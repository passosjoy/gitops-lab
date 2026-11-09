data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "ol9" {
  compartment_id           = oci_identity_compartment.lab.id
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = var.compute_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  compute_subnet_id = var.assign_public_ip ? oci_core_subnet.public.id : oci_core_subnet.app.id
  cloud_init = templatefile("${path.module}/templates/cloud-init.yaml", {
    bootstrap_k3s = var.bootstrap_k3s
    app_http_port = var.app_http_port
  })
}

resource "oci_core_instance" "app" {
  count               = var.create_compute ? 1 : 0
  compartment_id      = oci_identity_compartment.lab.id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "${local.name_prefix}-app"
  shape               = var.compute_shape

  dynamic "shape_config" {
    for_each = strcontains(var.compute_shape, "Flex") ? [1] : []
    content {
      ocpus         = var.compute_ocpus
      memory_in_gbs = var.compute_memory_gbs
    }
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ol9.images[0].id
  }

  create_vnic_details {
    subnet_id        = local.compute_subnet_id
    assign_public_ip = var.assign_public_ip
    nsg_ids          = [oci_core_network_security_group.app.id]
    hostname_label   = "app01"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(local.cloud_init)
  }

  freeform_tags = local.common_tags

  lifecycle {
    ignore_changes = [metadata, source_details[0].source_id]
  }
}

resource "oci_bastion_bastion" "lab" {
  count                        = var.create_bastion ? 1 : 0
  compartment_id               = oci_identity_compartment.lab.id
  name                         = "${local.name_prefix}-bastion"
  bastion_type                 = "STANDARD"
  target_subnet_id             = oci_core_subnet.app.id
  client_cidr_block_allow_list = [var.admin_cidr != "0.0.0.0/0" ? var.admin_cidr : var.allowed_ssh_cidr]
  max_session_ttl_in_seconds   = 10800

  freeform_tags = local.common_tags
}
