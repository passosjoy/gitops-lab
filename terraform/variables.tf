variable "region" {
  description = "Região OCI do laboratório."
  type        = string
  default     = "sa-saopaulo-1"
}

variable "config_profile" {
  description = "Perfil do ~/.oci/config."
  type        = string
  default     = "DEFAULT"
}

variable "tenancy_ocid" {
  description = "OCID da tenancy (usado em IAM/budget)."
  type        = string
}

variable "parent_compartment_ocid" {
  description = "Compartment pai onde o compartment do lab será criado (normalmente a tenancy)."
  type        = string
}

variable "project_name" {
  description = "Nome curto do projeto (sem espaços)."
  type        = string
  default     = "lab-oci"
}

variable "environment" {
  description = "Ambiente lógico."
  type        = string
  default     = "lab"
}

variable "owner" {
  description = "Responsável pelo laboratório (tag Owner)."
  type        = string
  default     = "seu-nome"
}

variable "cost_center" {
  description = "Centro de custo para FinOps (tag CostCenter)."
  type        = string
  default     = "estudos"
}

variable "vcn_cidr" {
  description = "CIDR da VCN."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Subnet pública (LB/bastion host, se usado)."
  type        = string
  default     = "10.0.1.0/24"
}

variable "app_subnet_cidr" {
  description = "Subnet privada de aplicação."
  type        = string
  default     = "10.0.2.0/24"
}

variable "db_subnet_cidr" {
  description = "Subnet privada de banco."
  type        = string
  default     = "10.0.3.0/24"
}

variable "allowed_ssh_cidr" {
  description = "CIDR administrativo autorizado no OCI Bastion. NUNCA use 0.0.0.0/0."
  type        = string
  default     = "203.0.113.10/32"
}

variable "ssh_public_key" {
  description = "Conteúdo da chave pública SSH (ssh-rsa/ssh-ed25519 ...)."
  type        = string
}

variable "adb_admin_password" {
  description = "Senha do ADMIN do ADB (12+ chars, maiúscula, minúscula, número e especial). Usada apenas se create_adb=true."
  type        = string
  sensitive   = true
  default     = null
}

variable "adb_db_name" {
  description = "DB name do ADB (alfanumérico, começa com letra, até 30 chars)."
  type        = string
  default     = "LABADB"
}

variable "adb_db_version" {
  description = "Versão do ADB (19c ou 23ai, conforme disponibilidade na região)."
  type        = string
  default     = "19c"
}

variable "adb_storage_gb" {
  description = "Storage do ADB em GB (Always Free: 20)."
  type        = number
  default     = 20
}

variable "adb_is_free_tier" {
  description = "Cria ADB no Always Free (20 GB, 1 OCPU)."
  type        = bool
  default     = true
}

variable "create_adb" {
  description = "Cria Autonomous Database (Oracle). A aplicação deste lab usa PostgreSQL; mantenha false e execute Postgres no cluster/compute, ou true apenas se adaptar a app para Oracle."
  type        = bool
  default     = false
}

variable "compute_shape" {
  description = "Shape do compute de aplicação. OCI Always Free: VM.Standard.A1.Flex (até 4 OCPU / 24 GB no total da tenancy)."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "compute_ocpus" {
  description = "OCPUs do compute flex (Always Free A1: 4)."
  type        = number
  default     = 4
}

variable "compute_memory_gbs" {
  description = "Memória (GB) do compute flex (Always Free A1: 24)."
  type        = number
  default     = 24
}

variable "assign_public_ip" {
  description = "Atribui IP público à instância (necessário para SSH direto/pipelines de deploy no lab). Em produção, prefira Bastion + IP privado."
  type        = bool
  default     = true
}

variable "admin_cidr" {
  description = "CIDR autorizado para SSH/admin (ex.: seu IP/32). Usado nas regras de NSG quando assign_public_ip=true."
  type        = string
  default     = "0.0.0.0/0" # substitua pelo seu IP/32 no tfvars
}

variable "app_http_port" {
  description = "Porta HTTP da aplicação/ingress exposta no host."
  type        = number
  default     = 80
}

variable "bootstrap_k3s" {
  description = "Instala Docker e k3s no cloud-init (single-node) para rodar a stack Kubernetes/GitOps."
  type        = bool
  default     = true
}

# --- OKE (trial/créditos) ---
variable "create_oke" {
  description = "Cria cluster OKE. Use com créditos trial (4.500h compute); após o trial, prefira VM Always Free + compose."
  type        = bool
  default     = false
}

variable "oke_kubernetes_version" {
  description = "Versão do Kubernetes no OKE (deixe null para usar a versão suportada mais recente disponível na região)."
  type        = string
  default     = null
}

variable "oke_node_shape" {
  description = "Shape dos nós do OKE. A1.Flex (Ampere) é recomendado quando disponível com créditos/trial."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "oke_node_ocpus" {
  description = "OCPUs por nó (shapes Flex)."
  type        = number
  default     = 2
}

variable "oke_node_memory_gbs" {
  description = "Memória por nó em GB (shapes Flex)."
  type        = number
  default     = 12
}

variable "oke_node_count" {
  description = "Quantidade de nós no node pool."
  type        = number
  default     = 2
}

variable "oke_node_image_id" {
  description = "OCID da imagem dos nós OKE (deixe null para selecionar automaticamente imagem OKE compatível com o shape)."
  type        = string
  default     = null
}

variable "create_iam" {
  description = "Cria grupo/policies/dynamic group de laboratório."
  type        = bool
  default     = true
}

variable "create_compute" {
  description = "Cria a instância de aplicação."
  type        = bool
  default     = true
}

variable "create_bastion" {
  description = "Cria o OCI Bastion."
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Cria log group e VCN flow logs."
  type        = bool
  default     = true
}

variable "budget_amount" {
  description = "Teto mensal do laboratório na moeda da tenancy."
  type        = number
  default     = 100
}

variable "budget_alert_email" {
  description = "E-mail para alertas de budget."
  type        = string
}
