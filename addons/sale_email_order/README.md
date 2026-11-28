# Ps-Tech module : Sale Email Order

## 19.0.1.0.0

-   New model 'sale.email.order' (Sales > Orders > Email Orders) that stores every inbound order email.
    Emails sent to the 'orders' mail alias create a record in state 'New'.
-   'New' emails are processed in the background by the cron 'Email Orders: Process with AI', triggered as soon as an
    email arrives (hourly as a fallback). The cron commits after each email. 'Process' (form and list) re-queues
    'New' / 'To Review' emails.
-   A draft quotation is only ever a proposal for staff: the module never confirms an order and never replies.
-   Extraction strategy (Sales > Configuration > Settings > Email Orders (AI)), each with its own options:
-   'Qwen only': local Ollama model (default 'qwen3.5:4b') returns category ('standard', 'complex', 'quote'),
    confidence and order lines as JSON.
-   'GPT-6.2 Sol only': the strong OpenAI model (key in env 'OPENAI_API_KEY') extracts every email.
-   'Qwen with cloud fallback': option 'Send to cloud when' = confidence below threshold, or Kev verification above
    the 'Kev error threshold'.
-   'Local-first risk gate': the small answer is scored by a calibrated risk gate ('data/hybrid_policy.json') with
    the Kev check and escalated above the risk cut. Options: 'Risk budget' (lowest risk, about 20% or 30% to cloud)
    and 'Local guard' (fake system instructions and old-order tracking questions go to review first).
-   'Current-sender authorization': only the current sender's unconditional dispatch instruction can draft; the
    rest is scored with 'data/authority_policy.json'. Options: 'Risk budget' and 'Draft short clear orders locally'
    (a root instruction whose catalogue lines are fully consumed drafts without the small model agreeing).
-   'Per-line authorization' (Stage 1): quoted history is clipped, the current turn is split into clauses,
    cancelled / conditional / historical clauses are dropped and each line must cite a dispatch clause with its
    catalogue item and quantity. Unresolved emails go to the strong model, the rest to review.
    Option 'Sort non-orders' (Stage 2, final system of the project report): non-orders are archived, silently
    attached to an open case of the same sender and company ('CASE-42', 'Case #42', 'case–42', 'CASE:42'),
    attached with an internal note on the case, or put in the human queue. A draft whose current turn still asks
    something gets 'Human follow-up'. 'Mark staff work complete' clears the follow-up without touching the quotation.
    Option 'Check orders for extra questions with the small model' (with 'Sort non-orders'): the small model is also
    asked whether a drafted order requests anything else (e.g. "Pls cnfrm the loading time"). It can only add the
    follow-up flag; if Ollama fails, the rules' answer stands.
-   Former strategy names (e.g. 'hybrid_guard30', 'authority_disposition') still work when set directly in the
    system parameters, as the evaluation scripts do.
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
