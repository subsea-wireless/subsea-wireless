# Contributing Parameters

## Before you start
1. **Always check for similar parameters** to what you plan to add/change.  
   *Example:* only one parameter for signal strength should exist. Can you extend the existing one instead?

2. **Do not change the JSON Schema in the same PR.**  
   If you think a new `representation` type or other schema change is needed, submit that as a **separate PR**.

---

## Additional guidelines for fields

- **`id`**  
  1–255. Make sure the ID is **unique**.

- **`name`**  
  Machine-readable description of the parameter, **snake_case** with **no whitespace** (≤256 chars).

- **`description`**  
  Human-readable description of the parameter. Fully describe how the parameter is to be **interpreted**, including **unit** and any **scaling** (e.g., “value is dB×10”).

- **`representation`**  
  Data type. **Keep to the list** in [the schema](./parameters_schema.json).

- **`minimum`**  
  Minimum value (inclusive) if applicable. **Omit** if the full data type range is allowed.

- **`maximum`**  
  Maximum value (inclusive) if applicable. **Omit** if the full data type range is allowed.

- **`valid integers`**  
  Enumeration of allowed numeric values (e.g., enums). **Omit** if any value in `minimum..maximum` is valid. Keep the list **short**.

- **`valid strings`**  
  Enumeration of allowed string values. **Omit** if any string is allowed or if you’re using `pattern` instead. Keep the list **short**.

- **`pattern`**  
  [See schema](./parameters_schema.json).  

- **`access`**  
  `"wet"` and `"dry"` interfaces, see [`README.md`](./README.md#access-flags). You must **explicitly set `true`** to enable read/write for a given interface. All unspecified flags default to **false**.

  **Access flags (inside `dry` / `wet`):**
  - `read` – interface may read the parameter.  
  - `write` – interface may write the parameter.  
  - `read_option` – read is optional to implement (vendor choice). **Requires** `read: true`.  
  - `write_option` – write is optional to implement. **Requires** `write: true`.  
  - `read_auth` – reading requires authenticated connection. **Requires** `read: true`.  
  - `write_auth` – writing requires authenticated connection. **Requires** `write: true`.

> **Defaults:** If a flag isn’t listed, it’s **false**.
