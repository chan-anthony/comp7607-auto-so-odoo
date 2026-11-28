# Runtime and reproduction

The integration branch extends the teammate baseline at `cc6313e`. Use
synthetic mail in an isolated `odoo_test` database. Never import a real inbox
into a run that can send mail text to a hosted model. The app creates quotations,
does not confirm sales or send outgoing customer mail.

* Odoo 19.0-20261123, PostgreSQL 15.20, Ollama 0.40.18 (observed runtime).
  The Compose tags are mutable; record container image IDs for a new run.
* Qwen: Ollama `qwen2.5:1.5b`, model digest prefix `65ec06548149`, Q4_K_M.
  Baseline uses the existing JSON prompt/few-shot examples, temperature zero,
  and the model-reported confidence (not token log probability).
* Strong extractor: OpenAI Responses API, `gpt-6.2-sol`. The project key is
  read from the environment, never stored in Odoo or included with the source.
  Confirm API and cost settings before enabling hosted inference. Keep the
  key in a Git-ignored project .env file. When modifying a web container's
  environment, save output from /tmp to the host before recreating it.
* Kev: [author's implementation](https://github.com/jaredpalmer/kev) at
  `556167b5b151152cb4101629e25d883e9ead5094`. Adapter
  `jaredpalmer/kev-0.8b@9a45d25eb2ab761841196625383fa1dff0e56c1e`,
  base `Qwen/Qwen3.5-0.8B-Base@dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`.
  Tested with Python 3.12.14, PyTorch 2.8.0+cpu and Transformers 5.24.1.
  Follow the author's installation procedure for that checkout with the serve
  extra, in a separate virtual environment. Run `python -m kev.serve --run
  jaredpalmer/kev-0.8b@9a45d25eb2ab761841196625383fa1dff0e56c1e --device cpu
  --host 127.0.0.1 --port 8008` as one command. Set OMP_NUM_THREADS and
  MKL_NUM_THREADS to 2 for the tested CPU configuration. The measured Windows
  run used an integrity-checked local snapshot of this adapter and base.
  Odoo addressed the host via Docker Desktop's host.docker.internal:8008.

On Windows run evaluation/setup_local.ps1 in PowerShell 7, then install the
Ollama model with `docker compose exec ollama ollama pull qwen2.5:1.5b`.
Open the local Odoo web address configured in .env (bootstrap default port
18069). Choose the email strategy under Sales settings. In Email Orders select
a processed record and Generate report. Strong and Kev modes are optional
when reproducing just the Qwen-only baseline.

To reproduce the native 20-message round, run evaluation/run_native.ps1 with
a fresh round name, chosen strategy, Python path and output directory. Pass
-AllowApi only for strategies authorized to call the hosted extractor. To
reproduce paired evaluation, generate manifest.json and stress-manifest.json
with build_cases.py and build_extended.py; run run_panel.ps1 for the three
calibration tiers (small precedes kev); freeze with replay_policies.py freeze.
Only then collect the test and stress splits and score them using
replay_policies.py score / stress. budget_curve.py accepts the data folder
then the split name, and summarize.py accepts the resulting policy-scores JSON.
Keep the native regression outputs distinct from the cached policy replay.
