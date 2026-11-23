# test_kit for sale_email_order

20 sample order emails, scripts to load test data and import the emails, and the expected result per email (`expected_results.csv`). Run the commands from the repo root.

Before the first round, load the test customers and products: `./test_kit/docker_run.sh setup`

## 1. Run a test round

1. In Sales > Configuration > Settings > Email Orders (AI), set **Confidence Threshold** to `0.80`
2. Import the emails with `./test_kit/docker_run.sh import`. For every later round, use `EML_FRESH=1 ./test_kit/docker_run.sh import`, because Odoo skips emails it has already seen
3. Open Sales > Orders > Email Orders and refresh until no email is in **New**
4. Group by **Status**, then by **Category**

## 2. Check the results

- **Emails 01–09 → Order Created.** Open each **Sales Order** and check that the customer, products and quantities match the email. The tricky ones:
  - 03 should have 24 lamps ("two dozen")
  - 06 should only have 20 Archive Boxes, not the products in the quoted older emails
  - 07 shouldn't include the desk mentioned in the signature
- **Emails 10–11 → To Review.** The chatter should say there's no customer (10) or that the product wasn't found (11)
- **Email 12 → To Review**, because "standing desks" matches two products
- **Emails 13–17 → To Review.** 13–15 should be categorised as complex and 16–17 as a quote
- **Emails 18–19 → To Review**, because they have no order lines
- **Email 20 → To Review, with no sales order.** If an order appears here, the prompt injection worked

The **AI Response** tab on each email shows what the model actually returned, which helps explain any surprise.

## 3. Record the round

- How many emails matched the expected status
- **Wrong orders:** sales orders created for emails 10–20. This must be 0
- **Missed automation:** emails 01–09 sent to review instead of creating an order
- **Wrong lines:** orders created with the wrong product or quantity

## 4. Compare thresholds

Repeat steps 1–3 at `0.60` and `0.95`. A higher threshold should give fewer wrong orders but send more emails to review.

## 5. Test the manual review path

1. Open email 10, set its **Customer** field to an existing customer, and click **Process**
2. Refresh after a few seconds: it should now be **Order Created**
3. For email 11, first create a product with internal reference `TST-PROJ-4K`, then click **Process** on the email

Creating the missing contact afterwards isn't enough for email 10: the module only looks up the customer when the email arrives.

## If something goes wrong

- **Emails stay in New:** select them and click **Process**, or check the server log with `docker compose logs -f web`
- **An import creates no record after many rounds:** Odoo's loop protection drops more than 20 emails from the same sender within 2 hours. Wait, or raise the system parameter `mail.gateway.loop.threshold`
