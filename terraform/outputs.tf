output "compartment_id" {
  description = "Compartment do laboratório."
  value       = oci_identity_compartment.lab.id
}

output "vcn_id" {
  description = "VCN do laboratório."
  value       = oci_core_vcn.lab.id
}

output "adb_id" {
  description = "OCID do Autonomous Database (quando create_adb=true)."
  value       = var.create_adb ? oci_database_autonomous_database.lab[0].id : null
}

output "adb_private_endpoint" {
  description = "Endpoint privado do ADB (quando create_adb=true)."
  value       = var.create_adb ? oci_database_autonomous_database.lab[0].private_endpoint : null
}

output "bucket_name" {
  description = "Bucket de objetos do laboratório."
  value       = oci_objectstorage_bucket.lab.name
}

output "compute_private_ip" {
  description = "IP privado da instância de aplicação."
  value       = var.create_compute ? oci_core_instance.app[0].private_ip : null
}

output "compute_public_ip" {
  description = "IP público da instância de aplicação (quando assign_public_ip=true)."
  value       = var.create_compute && var.assign_public_ip ? oci_core_instance.app[0].public_ip : null
}

output "bastion_id" {
  description = "OCID do OCI Bastion."
  value       = var.create_bastion ? oci_bastion_bastion.lab[0].id : null
}

output "alerts_topic_id" {
  description = "Topic de notificações."
  value       = oci_ons_notification_topic.lab.id
}

output "ssh_command" {
  description = "Comando SSH para a instância (ajuste caminho da chave)."
  value       = var.create_compute && var.assign_public_ip ? "ssh -i <SUA_CHAVE_PRIVADA> opc@${oci_core_instance.app[0].public_ip}" : "Use OCI Bastion para acessar a instância privada."
}

output "oke_cluster_id" {
  description = "OCID do cluster OKE (quando create_oke=true)."
  value       = var.create_oke ? oci_containerengine_cluster.lab[0].id : null
}

output "oke_cluster_name" {
  description = "Nome do cluster OKE (quando create_oke=true)."
  value       = var.create_oke ? oci_containerengine_cluster.lab[0].name : null
}

output "oke_kubeconfig_hint" {
  description = "Comando para gerar kubeconfig do OKE (ajuste region/profile)."
  value       = var.create_oke ? "oci ce cluster create-kubeconfig --cluster-id ${oci_containerengine_cluster.lab[0].id} --file $HOME/.kube/config --region ${var.region} --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT" : null
}
