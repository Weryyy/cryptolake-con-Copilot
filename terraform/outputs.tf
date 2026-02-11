output "bronze_bucket" {
  value = module.storage.bronze_bucket_name
}

output "silver_bucket" {
  value = module.storage.silver_bucket_name
}

output "gold_bucket" {
  value = module.storage.gold_bucket_name
}
