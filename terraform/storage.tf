data "oci_objectstorage_namespace" "lab" {
  compartment_id = oci_identity_compartment.lab.id
}

resource "oci_kms_vault" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  display_name   = "${local.name_prefix}-vault"
  vault_type     = "DEFAULT"

  freeform_tags = local.common_tags
}

resource "oci_kms_key" "lab" {
  compartment_id      = oci_identity_compartment.lab.id
  display_name        = "${local.name_prefix}-key"
  management_endpoint = oci_kms_vault.lab.management_endpoint

  key_shape {
    algorithm = "AES"
    length    = 32
  }

  freeform_tags = local.common_tags
}

resource "oci_objectstorage_bucket" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  namespace      = data.oci_objectstorage_namespace.lab.namespace
  name           = "${local.name_prefix}-bucket"
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
  storage_tier   = "Standard"
  kms_key_id     = oci_kms_key.lab.id

  freeform_tags = local.common_tags
}

resource "oci_objectstorage_object_lifecycle_policy" "lab" {
  namespace = data.oci_objectstorage_namespace.lab.namespace
  bucket    = oci_objectstorage_bucket.lab.name

  rules {
    name        = "archive-after-90-days"
    action      = "ARCHIVE"
    time_amount = 90
    time_unit   = "DAYS"
    target      = "objects/"
    is_enabled  = true
  }

  rules {
    name        = "delete-after-365-days"
    action      = "DELETE"
    time_amount = 365
    time_unit   = "DAYS"
    target      = "objects/"
    is_enabled  = true
  }
}
