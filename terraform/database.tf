resource "oci_database_autonomous_database" "lab" {
  count                       = var.create_adb ? 1 : 0
  compartment_id              = oci_identity_compartment.lab.id
  display_name                = "${local.name_prefix}-adb"
  db_name                     = var.adb_db_name
  db_version                  = var.adb_db_version
  db_workload                 = "OLTP"
  cpu_core_count              = 1
  data_storage_size_in_gb     = var.adb_storage_gb
  admin_password              = var.adb_admin_password
  license_model               = "LICENSE_INCLUDED"
  is_auto_scaling_enabled     = true
  is_mtls_connection_required = true
  is_free_tier                = var.adb_is_free_tier

  # Endpoint privado: sem acesso público.
  subnet_id  = oci_core_subnet.db.id
  nsg_ids    = [oci_core_network_security_group.db.id]
  kms_key_id = oci_kms_key.lab.id

  freeform_tags = local.common_tags

  lifecycle {
    precondition {
      condition     = var.adb_admin_password != null && length(var.adb_admin_password) >= 12
      error_message = "Defina adb_admin_password (12+ caracteres) quando create_adb=true, ou mantenha create_adb=false e use PostgreSQL para esta aplicação."
    }
  }
}
