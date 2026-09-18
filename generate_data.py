import csv
from pathlib import Path

Path("data").mkdir(exist_ok=True)

# 1. Global Sales (General Multi-Region Multi-Currency)
global_sales = [
    ["Order_ID", "Date", "Country", "Currency", "Revenue", "Quantity", "Category"],
    ["ORD-1001", "2026-01-05", "DE", "EUR", 4500.00, 15, "Cloud Storage"],
    ["ORD-1002", "2026-01-06", "GB", "GBP", 3200.00, 8, "Analytics Suite"],
    ["ORD-1003", "2026-01-08", "IN", "INR", 125000.00, 20, "Security Gateway"],
    ["ORD-1004", "2026-01-10", "US", "USD", 5400.00, 10, "Cloud Storage"],
    ["ORD-1005", "2026-01-11", "DE", "EUR", -450.00, 1, "Analytics Suite"],
    ["ORD-1006", "2026-01-14", "US", "USD", 185000.00, 80, "Enterprise Support"],
    ["ORD-1007", "2026-01-15", "GB", "GBP", 2100.00, 5, "Security Gateway"],
    ["ORD-1008", "2026-01-18", "IN", "INR", 89000.00, 12, "Cloud Storage"],
]

with open("data/global_sales.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(global_sales)

# 2. EMEA Subscriptions
emea_subscriptions = [
    ["Order_ID", "Date", "Country", "Currency", "Revenue", "Quantity", "Category"],
    ["EMEA-2001", "2026-02-01", "FR", "EUR", 12400.00, 24, "SaaS Enterprise"],
    ["EMEA-2002", "2026-02-03", "GB", "GBP", 9800.00, 16, "DevOps Pipeline"],
    ["EMEA-2003", "2026-02-05", "CH", "CHF", 14500.00, 10, "SaaS Enterprise"],
    ["EMEA-2004", "2026-02-07", "SE", "SEK", 85000.00, 30, "Security Gateway"],
    ["EMEA-2005", "2026-02-10", "DE", "EUR", -1200.00, 2, "DevOps Pipeline"],
    ["EMEA-2006", "2026-02-12", "NL", "EUR", 7600.00, 12, "SaaS Enterprise"],
    ["EMEA-2007", "2026-02-14", "GB", "GBP", 34000.00, 50, "Analytics Suite"],
    ["EMEA-2008", "2026-02-18", "FR", "EUR", 6200.00, 8, "Security Gateway"],
    ["EMEA-2009", "2026-02-22", "CH", "CHF", 11200.00, 15, "DevOps Pipeline"],
    ["EMEA-2010", "2026-02-25", "DE", "EUR", 18900.00, 28, "SaaS Enterprise"],
]

with open("data/emea_subscriptions.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(emea_subscriptions)

# 3. APAC Retail & Commerce
apac_retail = [
    ["Order_ID", "Date", "Country", "Currency", "Revenue", "Quantity", "Category"],
    ["APAC-3001", "2026-03-01", "JP", "JPY", 850000.00, 45, "Consumer Hardware"],
    ["APAC-3002", "2026-03-03", "SG", "SGD", 14200.00, 18, "Cloud Hosting"],
    ["APAC-3003", "2026-03-06", "AU", "AUD", 22500.00, 22, "Enterprise Software"],
    ["APAC-3004", "2026-03-08", "IN", "INR", 450000.00, 60, "Cloud Hosting"],
    ["APAC-3005", "2026-03-11", "JP", "JPY", -25000.00, 1, "Consumer Hardware"],
    ["APAC-3006", "2026-03-14", "SG", "SGD", 31000.00, 35, "Enterprise Software"],
    ["APAC-3007", "2026-03-17", "AU", "AUD", 18900.00, 15, "Consumer Hardware"],
    ["APAC-3008", "2026-03-20", "IN", "INR", 980000.00, 110, "Cloud Hosting"],
]

with open("data/apac_retail_q3.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(apac_retail)

# 4. US Enterprise Direct
us_enterprise = [
    ["Order_ID", "Date", "Country", "Currency", "Revenue", "Quantity", "Category"],
    ["USE-4001", "2026-04-01", "US", "USD", 65000.00, 40, "Dedicated Infrastructure"],
    ["USE-4002", "2026-04-03", "CA", "CAD", 48000.00, 25, "Cybersecurity Audit"],
    ["USE-4003", "2026-04-06", "US", "USD", 120000.00, 75, "AI Engine Licensing"],
    ["USE-4004", "2026-04-10", "US", "USD", -8500.00, 3, "Cybersecurity Audit"],
    ["USE-4005", "2026-04-12", "CA", "CAD", 72000.00, 38, "Dedicated Infrastructure"],
    ["USE-4006", "2026-04-16", "US", "USD", 340000.00, 150, "AI Engine Licensing"],
    ["USE-4007", "2026-04-20", "US", "USD", 95000.00, 50, "Dedicated Infrastructure"],
]

with open("data/us_enterprise_direct.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(us_enterprise)

print("Generated all enterprise datasets successfully.")