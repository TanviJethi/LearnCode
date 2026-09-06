# LearnCode - Programming by Logic

Write simple programs in plain English and watch them execute step by step.
Runs entirely on your machine — no API keys, no internet connection, no external AI calls.

## What you can write

- `Create x with 10.` / `Set x to 10.`
- `Add 5 to x.` / `Subtract 5 from x.` / `Multiply x by 2.` / `Divide x by 2.`
- `Print x.` / `Print 'some text'.`
- `Repeat 5 times, add 1 to x.`
- `If x > 10, print 'Big'. Otherwise print 'Small'.`

Example:
```
Create x with 10. Add 5 to x. Print x.
```

## Files

- `app.py` — Streamlit UI: input box, step-by-step trace viewer, variables/output/code tabs
- `parser.py` — Local rule-based parser: plain English -> structured steps (no AI involved)
- `interpreter.py` — Sandboxed interpreter that safely executes the structured steps
- `requirements.txt` — Just Streamlit
- `.streamlit/config.toml` — App theme/config
