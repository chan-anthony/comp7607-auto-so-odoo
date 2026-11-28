# Ps-Tech module : Sale Email Order

## 19.0.1.0.0

-   New model 'sale.email.order' (Sales > Orders > Email Orders) that stores every inbound order email.
    Emails sent to the 'orders' mail alias create a record in state 'New'.
-   'New' emails are processed in the background by the cron 'Email Orders: Process with AI', triggered as soon as an
    email arrives (hourly as a fallback). The cron commits after each email. 'Process' (form and list) re-queues
    'New' / 'To Review' emails.
-   A draft quotation is only ever a proposal for staff: the module never confirms an order and never replies.
-   Extraction strategies below are chosen in Sales > Configuration > Settings > Email Orders (AI).
-   Strategy 'Qwen only': local Ollama model (default 'qwen2.5:1.5b') returns category ('standard', 'complex', 'quote'),
    confidence and order lines as JSON.
-   Strategy 'GPT-6.2 Sol only' / 'Qwen with confidence handoff': the strong OpenAI model (key in env 'OPENAI_API_KEY')
    extracts all emails / only those below the confidence threshold.
-   Strategy 'Qwen with Kev verification' and 'Local-first' / 'Current sender' budgets: the small answer is checked by a
    calibrated risk gate (policies 'data/hybrid_policy.json' and 'data/authority_policy.json') and escalated
    to the strong model above the risk threshold.
-   Strategy 'Scoped current-sender authorization': the root dispatch clause can draft locally when every catalogue line
    is fully consumed.
-   Strategy 'Per-line current authorization' (Stage 1): quoted history is clipped, the current turn is split into clauses,
    cancelled / conditional / historical clauses are dropped and each line must cite a dispatch clause with its
    catalogue item and quantity. Unresolved emails go to the strong model, the rest to review.
-   Strategy 'Line authorization + non-order disposition' (Stage 2): non-orders are archived, silently attached to an open
    case of the same sender and company ('CASE-42', 'Case #42', 'case–42', 'CASE:42'), attached with an internal
    note on the case, or put in the human queue. A draft whose current turn still asks something gets
    'Human follow-up'. 'Mark staff work complete' clears the follow-up without touching the quotation.
-   Order created: 'standard' + confidence >= threshold (or line authorization) + known customer + all products
    found -> draft quotation, email 'Order Created'. Any other case goes to 'To Review' with a 'Review Reason'.
-   The customer is the gateway sender, else the contact whose email matches 'email_from' (looked up again on each
    processing, so imported emails and contacts created later work too).
-   Products are matched by internal reference first, then by name; an ambiguous match goes to review.
-   A malformed AI answer, a connection error or an order creation error sends the email to review.
-   'Test Connection' next to the Ollama URL lists the installed models (smallest first) as 'Small Model' options.
-   'Use Token Probabilities': the confidence becomes the probability of the token where the category value starts;
    falls back to the model estimate when no usable logprobs are returned ('Confidence Source').
-   Category, confidence, processing time and the inference trace are stored on each email; 'Generate report'
    prints the decision path, Kev checks and strong-model token usage of the selected emails.
-   Multi-company record rule on 'sale.email.order'.
-   Not implemented from the report: the learned residual-sentence follow-up classifier (hashed logistic
    regression); follow-up cues on drafts are the deterministic rules only.
