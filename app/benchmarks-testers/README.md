Simple `pyre` benchmarks.

- `simple_ok.py`:
  - All functions are correctly typed.
  - `pyre check` should report **no errors** for this file.

- `simple_type_errors.py`:
  - Contains intentional type mismatches:
    - `bad_add` returns a `str` but is annotated to return `int`.
    - `use_wrong_types` calls `bad_add` with a `str` instead of `int`.
  - `pyre check` should report **errors** for this file.

Run from the project root (where `.pyre_configuration` lives):

```bash
pyre check app/benchmarks/simple_ok.py
pyre check app/benchmarks/simple_type_errors.py
```

