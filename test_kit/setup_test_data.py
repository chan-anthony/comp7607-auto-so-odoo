# Creates the customers and products used by the sample emails.
# Run inside the Odoo shell:  odoo-bin shell -d <db> --no-http < setup_test_data.py
# Safe to run several times: existing records (same email / internal reference) are reused.

CUSTOMERS = [
    ("Bright Office Supplies Ltd", "Sarah Collins", "purchasing@brightoffice.example"),
    ("Harbour Dental Group", "Dr. Wei Lam", "ops@harbourdental.example"),
    ("Kestrel Coworking", "Tom Reyes", "hello@kestrelcowork.example"),
    ("Pinecrest School District", "Linda Okafor", "procurement@pinecrest-schools.example"),
    ("Atelier Lumière SARL", "Julie Moreau", "achats@atelier-lumiere.example"),
    # alex.novak@unknown-startup.example is deliberately NOT created (email 10 tests an unknown sender)
]

PRODUCTS = [  # (internal reference, name, sales price)
    ("TST-DESK-140", "Standing Desk 140cm", 4200.0),
    ("TST-DESK-180", "Standing Desk 180cm", 4900.0),
    ("TST-CHAIR-MESH", "Ergonomic Mesh Chair", 1690.0),
    ("TST-ARM-DUAL", "Dual Monitor Arm", 780.0),
    ("TST-PED-3D", "Mobile Pedestal 3 Drawers", 1150.0),
    ("TST-LAMP-LED", "LED Desk Lamp", 320.0),
    ("TST-BOX-A4", "Archive Box A4", 18.0),
    ("TST-SHELF-80", "Steel Shelf 80cm", 650.0),
    ("TST-SHELF-120", "Steel Shelf 120cm", 890.0),
    ("TST-WB-120", "Magnetic Whiteboard 120x90", 990.0),
    # TST-PROJ-4K is deliberately NOT created (email 11 tests an unknown product)
]

Partner = env["res.partner"]
for company_name, contact_name, email in CUSTOMERS:
    company = Partner.search([("name", "=", company_name), ("is_company", "=", True)], limit=1) \
        or Partner.create({"name": company_name, "is_company": True})
    contact = Partner.search([("email", "=ilike", email)], limit=1)
    if not contact:
        contact = Partner.create({"name": contact_name, "email": email, "parent_id": company.id})
    print(f"customer  {email:42} -> {contact.display_name} (id {contact.id})")

Product = env["product.product"].with_context(active_test=False)
for code, name, price in PRODUCTS:
    product = Product.search([("default_code", "=", code)], limit=1)
    if not product:
        product = Product.create({"name": name, "default_code": code, "list_price": price, "sale_ok": True})
    elif not product.active or not product.sale_ok:
        product.write({"active": True, "sale_ok": True})
    print(f"product   {code:15} -> {product.display_name} (id {product.id})")

# Warn about name clashes that would make name matching ambiguous (e.g. demo data).
for code, name, price in PRODUCTS:
    clash = env["product.product"].search_count([("sale_ok", "=", True), ("name", "ilike", name)])
    if clash > 1:
        print(f"WARNING: {clash} sellable products match '{name}' by name; name-based emails may go to review.")

env.cr.commit()
print("Test data ready.")
