Extract TypeScript interface definitions from the selected Python Pydantic models or dataclasses.

Rules:
- `str` → `string`, `int | float` → `number`, `bool` → `boolean`
- `list[T]` → `T[]`, `dict[str, T]` → `Record<string, T>`
- Optional fields (`None` default) → add `?` suffix
- Preserve docstrings as JSDoc comments
