# Budget mensuel par projet : e-mail aux administrateurs de la facturation à 50, 90 et 100 %
# de la dépense réelle, et à 100 % de la dépense prévue pour le mois.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "Observatoire CEMAC ${var.environment}"

  budget_filter {
    projects               = ["projects/${var.project_number}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = var.currency
      units         = tostring(var.amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
}
