"""
File parser utility for bulk product uploads.

Reads CSV/XLSX files in chunks, validates required columns,
and yields validated/rejected row dicts for the service layer.
"""
import io
import json
import logging
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {"sku", "name"}

OPTIONAL_COLUMNS = {
    "description", "brand", "category", "subcategory", "unit",
    "attributes", "is_active",
}

ALL_KNOWN_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

ALLOWED_EXTENSIONS = {"csv", "xlsx"}

# Rows processed per chunk to cap memory usage when loading 85k-row files
CHUNK_SIZE = 1_000


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_file_extension(filename: str) -> str:
    """Return lowercase extension without the dot."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_extension(filename: str) -> str:
    """Return the extension or raise ValueError."""
    ext = get_file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    return ext


def validate_columns(columns: List[str]) -> List[str]:
    """Check that all required columns exist.

    Returns the list of missing required columns (empty = OK).
    """
    normalised = {c.strip().lower() for c in columns}
    return [col for col in REQUIRED_COLUMNS if col not in normalised]


def _parse_attributes(raw: Any) -> Tuple[Optional[Dict], Optional[str]]:
    """Parse the `attributes` cell into a dict.

    Accepts: dict already, JSON string, NaN/None (→ empty dict), empty string.
    Returns (parsed_dict, error_message).
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)) or raw == "":
        return {}, None
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return None, "attributes must be a JSON object (dict), not an array or scalar."
            return parsed, None
        except (json.JSONDecodeError, ValueError) as exc:
            return None, f"attributes is not valid JSON: {exc}"
    return None, f"attributes has unexpected type '{type(raw).__name__}'."


def _parse_bool(raw: Any, field: str) -> Tuple[Optional[bool], Optional[str]]:
    """Coerce a cell to bool. Accepts True/False, 1/0, 'true'/'false' strings."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return True, None  # default
    if isinstance(raw, bool):
        return raw, None
    if isinstance(raw, (int, float)):
        return bool(raw), None
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in ("true", "1", "yes"):
            return True, None
        if v in ("false", "0", "no"):
            return False, None
    return None, f"'{field}' must be true/false, got '{raw}'."


def _coerce_str(raw: Any, field: str, max_len: int) -> Tuple[Optional[str], Optional[str]]:
    """Coerce a cell to a stripped string within max_len."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None, None  # optional field absent
    val = str(raw).strip()
    if not val:
        return None, None
    if len(val) > max_len:
        return None, f"'{field}' exceeds {max_len} characters."
    return val, None


# ── Core reader ───────────────────────────────────────────────────────────────

def read_file_to_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse file bytes into a DataFrame.

    Raises ValueError for unsupported types or empty files.
    """
    ext = validate_extension(filename)

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    buf = io.BytesIO(file_bytes)

    if ext == "csv":
        try:
            df = pd.read_csv(buf, dtype=str, keep_default_na=False, na_values=[""])
        except Exception as exc:
            raise ValueError(f"Failed to parse CSV: {exc}") from exc
    else:  # xlsx
        try:
            df = pd.read_excel(buf, dtype=str, keep_default_na=False, na_values=[""])
        except Exception as exc:
            raise ValueError(f"Failed to parse XLSX: {exc}") from exc

    if df.empty:
        raise ValueError("The uploaded file contains no data rows.")

    # Normalise column names to lowercase, stripped
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def validate_and_parse_rows(
    df: pd.DataFrame,
    existing_skus: set,
) -> Generator[Tuple[int, Optional[Dict], Optional[str]], None, None]:
    """Yield (row_number, parsed_dict_or_None, error_string_or_None) for every row.

    row_number is 1-based (matches spreadsheet row visible to the user).
    A yielded error means the row is rejected; a yielded dict means it is valid.

    De-duplication within the file is handled by tracking seen_skus.
    De-duplication against the database is handled via the `existing_skus` set
    passed in by the service (populated with one efficient bulk query before
    processing starts).
    """
    seen_skus: Dict[str, int] = {}  # sku → first row number

    for chunk_start in range(0, len(df), CHUNK_SIZE):
        chunk = df.iloc[chunk_start: chunk_start + CHUNK_SIZE]

        for local_idx, row in chunk.iterrows():
            row_num = int(local_idx) + 2  # +1 header, +1 because 0-indexed

            errors = []

            # ── Required fields ───────────────────────────────────────────────
            sku_raw = row.get("sku", "")
            sku = str(sku_raw).strip() if sku_raw not in (None, "", float("nan")) else ""
            # Also catch pandas' string representation of NaN when dtype=str
            if sku.lower() == "nan":
                sku = ""
            if not sku:
                errors.append("'sku' is required and cannot be blank.")
            elif len(sku) > 100:
                errors.append("'sku' exceeds 100 characters.")

            name_raw = row.get("name", "")
            name = str(name_raw).strip() if name_raw not in (None, "", float("nan")) else ""
            if not name:
                errors.append("'name' is required and cannot be blank.")
            elif len(name) > 255:
                errors.append("'name' exceeds 255 characters.")

            # ── Optional string fields ────────────────────────────────────────
            description, e = _coerce_str(row.get("description"), "description", 65535)
            if e: errors.append(e)

            brand, e = _coerce_str(row.get("brand"), "brand", 100)
            if e: errors.append(e)

            category, e = _coerce_str(row.get("category"), "category", 100)
            if e: errors.append(e)

            subcategory, e = _coerce_str(row.get("subcategory"), "subcategory", 100)
            if e: errors.append(e)

            unit, e = _coerce_str(row.get("unit"), "unit", 50)
            if e: errors.append(e)

            # ── JSONB attributes ──────────────────────────────────────────────
            attributes, e = _parse_attributes(row.get("attributes"))
            if e: errors.append(e)

            # ── Boolean is_active ─────────────────────────────────────────────
            is_active, e = _parse_bool(row.get("is_active"), "is_active")
            if e: errors.append(e)

            # ── SKU duplication checks ────────────────────────────────────────
            if sku and not errors:
                if sku in seen_skus:
                    errors.append(
                        f"Duplicate SKU within file (first seen at row {seen_skus[sku]})."
                    )
                elif sku in existing_skus:
                    errors.append(f"SKU '{sku}' already exists in the database.")

            if errors:
                yield row_num, None, "; ".join(errors)
                continue

            # Mark SKU as seen for in-file dedup tracking
            seen_skus[sku] = row_num

            yield row_num, {
                "sku": sku,
                "name": name,
                "description": description,
                "brand": brand,
                "category": category,
                "subcategory": subcategory,
                "unit": unit,
                "attributes": attributes or {},
                "is_active": is_active if is_active is not None else True,
            }, None
