resource "oci_ons_notification_topic" "lab" {
  compartment_id = oci_identity_compartment.lab.id
  name           = "${local.name_prefix}-alerts"
  description    = "Alertas do laboratório OCI."

  freeform_tags = local.common_tags
}

resource "oci_ons_subscription" "email" {
  compartment_id = oci_identity_compartment.lab.id
  topic_id       = oci_ons_notification_topic.lab.id
  protocol       = "EMAIL"
  endpoint       = var.budget_alert_email

  freeform_tags = local.common_tags
}

resource "oci_monitoring_alarm" "adb_cpu" {
  count                 = var.create_adb ? 1 : 0
  compartment_id        = oci_identity_compartment.lab.id
  display_name          = "${local.name_prefix}-adb-cpu-high"
  metric_compartment_id = oci_identity_compartment.lab.id
  namespace             = "oci_autonomous_database"
  query                 = "CpuUtilization[5m].mean() > 80"
  severity              = "WARNING"
  destinations          = [oci_ons_notification_topic.lab.id]
  pending_duration      = "PT5M"
  resolution            = "PT1M"
  body                  = "CPU do ADB acima de 80% por 5 minutos. Verifique carga e plano de execução."
  is_enabled            = true

  freeform_tags = local.common_tags
}

