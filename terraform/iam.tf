resource "oci_identity_compartment" "lab" {
  compartment_id = var.parent_compartment_ocid
  name           = local.compartment_name
  description    = "Laboratório OCI — ${var.project_name} (${var.environment})"
  enable_delete  = true

  freeform_tags = local.common_tags
}

resource "oci_identity_group" "operators" {
  count          = var.create_iam ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-operators"
  description    = "Operadores do laboratório (adicione usuários manualmente)."

  freeform_tags = local.common_tags
}

resource "oci_identity_policy" "operators" {
  count          = var.create_iam ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-operators-policy"
  description    = "Permissões de laboratório, escopadas ao compartment do projeto."

  statements = [
    "Allow group ${oci_identity_group.operators[0].name} to manage instance-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage database-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage virtual-network-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage object-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage bastion-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage vaults in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage keys in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage monitoring-alarms in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage log-groups in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to read metrics in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage cluster-family in compartment ${oci_identity_compartment.lab.name}",
    "Allow group ${oci_identity_group.operators[0].name} to manage repos in compartment ${oci_identity_compartment.lab.name}",
  ]

  freeform_tags = local.common_tags
}

resource "oci_identity_dynamic_group" "instances" {
  count          = var.create_iam ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-instances"
  description    = "Instâncias do laboratório (instance principal)."
  matching_rule  = "instance.compartment.id = '${oci_identity_compartment.lab.id}'"

  freeform_tags = local.common_tags
}

resource "oci_identity_policy" "instances" {
  count          = var.create_iam ? 1 : 0
  compartment_id = var.tenancy_ocid
  name           = "${local.name_prefix}-instances-policy"
  description    = "Permite que instâncias do lab leiam Object Storage sem chave."

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.instances[0].name} to read object-family in compartment ${oci_identity_compartment.lab.name}",
  ]

  freeform_tags = local.common_tags
}
