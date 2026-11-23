# Ps-Tech module : sale_email_order

## 19.0.1.0.0

-   New model 'sale.email.order' (Sales > Orders > Email Orders) that stores every inbound order email.
    Emails sent to the 'orders' mail alias create a record in state 'New'.
-   'New' emails are processed in the background by the cron 'Email Orders: Process with AI', which is triggered
    as soon as an email arrives (and runs hourly as a fallback). The cron commits after each email.
-   Each email is sent to a small local model hosted by Ollama (default 'qwen2.5:1.5b'). The model returns a
    category ('standard', 'complex' or 'quote'), a confidence score and the ordered products/quantities as JSON.
-   Order created: 'standard' + confidence >= threshold + known customer + all products found -> a quotation is
    created and the email is set to 'Order Created'.
-   To Review: any other case goes to the human review queue. The reason is shown in 'Review Reason' (list and form)
    and logged in the chatter.
-   The customer is the gateway sender, or else the contact whose email matches 'email_from' (looked up again on each
    processing, so imported emails and contacts created later work too).
-   The AI answer is sanitized (only the JSON object is kept and validated). A malformed answer, a connection error
    or an order creation error sends the email to review instead of blocking the queue.
-   Products are matched by internal reference first, then by name; an ambiguous match goes to review.
-   'Process' button (form and list header) puts one or many emails back in the queue (batch).
-   New settings in Sales > Configuration > Settings > Email Orders (AI): Ollama URL, model name and confidence threshold.
-   'Test Connection' button next to the Ollama URL: checks the server, then fills 'Small Model' with the models
    installed on it (smallest first, with their parameter size) so the model is picked from a list.
-   Category, confidence and processing time are stored on each email so the routing can be compared in list
    view (group by Status / Category) across different thresholds.
-   Multi-company record rule on 'sale.email.order'.
-   Optional setting 'Use Token Probabilities': Ollama returns the token log probabilities (logprobs) and the
    confidence becomes the probability of the token where the category value starts (the categories start with
    different letters, so this token decides the category). Falls back to the model's self-reported estimate when
    no usable logprobs are returned. 'Confidence Source' on each email shows which one was used.

Note: only the small model is used in this version; the large-model cascade from the proposal is not implemented
and low-confidence emails go straight to the review queue.
