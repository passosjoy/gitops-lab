terraform {
  required_version = ">= 1.6.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }

  # Para produção/lab compartilhado, use state remoto.
  # A OCI expõe um backend S3-compatível (Object Storage) ou use OCI Resource Manager.
  # backend "s3" {
  #   bucket                      = "tfstate-lab"
  #   key                         = "oci-lab/terraform.tfstate"
  #   region                      = "sa-saopaulo-1"
  #   endpoint                    = "https://<namespace>.compat.objectstorage.sa-saopaulo-1.oraclecloud.com"
  #   access_key                  = "***"
  #   secret_key                  = "***"
  #   skip_region_validation      = true
  #   skip_credentials_validation = true
  #   skip_requesting_account_id  = true
  #   skip_s3_checksum            = true
  # }
}

provider "oci" {
  region              = var.region
  config_file_profile = var.config_profile
}
