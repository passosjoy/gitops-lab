locals {
  name_prefix      = "${var.project_name}-${var.environment}"
  compartment_name = "${local.name_prefix}-cmp"

  common_tags = {
    Project            = var.project_name
    Environment        = var.environment
    Owner              = var.owner
    CostCenter         = var.cost_center
    ManagedBy          = "terraform"
    DataClassification = "internal"
  }
}
