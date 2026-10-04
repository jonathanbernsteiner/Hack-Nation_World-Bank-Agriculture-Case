"""The Supabase migration (#19) must keep #7's columns and fixed lists, so the two ledgers can't drift apart."""

import hashlib
import re
from pathlib import Path

import pytest

from farm_ledger import Activity, BuyerType, Currency, Kind, PaidHow, Symptom, Unit
from farm_ledger.db import ENTRY_FIELDS
from farm_ledger.enums import CoffeeForm, CoffeeType

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
FIXED_LISTS = {"kind": Kind, "unit": Unit, "currency": Currency, "buyer_type": BuyerType,
               "paid_how": PaidHow, "activity": Activity, "symptom": Symptom,
               "coffee_form": CoffeeForm, "coffee_type": CoffeeType}
# sha256 of the normalised SQL (see `normalised`); checked against the live
# supabase_migrations.schema_migrations statements for 20261003234752 on 2026-10-03.
APPLIED_LEDGER_SQL_SHA256 = "a3dc06635dd1e25244cfd993b96b74838698c3b4e761f8a89585bb1290f76b45"


@pytest.fixture(scope="module")
def sql():
    (path,) = MIGRATIONS.glob("*_ledger_tables.sql")
    return path.read_text()


def columns(sql, table):
    body = re.search(rf"create table public\.{table} \((.*?)\n\);", sql, re.S).group(1)
    return {m.group(1) for m in re.finditer(r"^ {4}(\w+) ", body, re.M)}


def normalised(sql):
    """The SQL without comments, whitespace collapsed: only a real DDL change alters it."""
    return " ".join(re.sub(r"--[^\n]*", "", sql).split())


def all_migrations():
    return normalised("\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))).lower()


def uncommented_sql():
    """Every migration in filename order, comments removed."""
    text = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
    return re.sub(r"--[^\n]*", "", text)


def check_lists():
    """column -> allowed values; the last `check (col in (...))` for a column wins."""
    found = re.finditer(r"check\s*\(\s*(\w+)\s+in\s*\(([^)]*)\)\)", uncommented_sql())
    return {m.group(1): re.findall(r"'([^']*)'", m.group(2)) for m in found}


def migrated_columns(table):
    """`create table public.<table>` columns plus every `alter table public.<table> ... add column`."""
    text = uncommented_sql()
    created = re.search(rf"create table public\.{table} \((.*?)\n\);", text, re.S).group(1)
    names = {m.group(1) for m in re.finditer(r"^ {4}(\w+) ", created, re.M)} - {"unique", "primary"}
    for alter in re.finditer(rf"alter table public\.{table}\b(.*?);", text, re.S):
        names |= set(re.findall(r"add column (\w+)", alter.group(1)))
    return names


def test_check_lists_match_enums_after_all_migrations():
    lists = check_lists()
    for column, enum in FIXED_LISTS.items():
        assert lists[column] == [m.value for m in enum], column


def test_currency_includes_ugx():
    assert "UGX" in [m.value for m in Currency]
    assert "UGX" in check_lists()["currency"]


def test_entries_columns_include_coffee_form_type_amount_kg():
    assert {"coffee_form", "coffee_type", "amount_kg"} <= migrated_columns("entries")
    assert {"id", "call_id", "farmer_id", *ENTRY_FIELDS} <= migrated_columns("entries")


def test_status_default_processed_for_existing_rows():
    text = uncommented_sql()
    assert re.search(r"add column status text not null default 'processed'", text)
    assert "update public.calls set source = 'synthetic' where source is null" in text


def test_conversation_id_unique():
    assert re.search(r"add column conversation_id text unique", uncommented_sql())


def test_coffee_form_rejects_unknown_value():
    """'beans' is not a coffee form, and amount_kg must be positive."""
    text = uncommented_sql()
    assert "beans" not in check_lists()["coffee_form"]
    assert "check (amount_kg > 0)" in text


def test_view_is_security_invoker_and_revoked():
    text = uncommented_sql()
    assert "create view public.coffee_sale_prices with (security_invoker = true)" in text
    assert "revoke all on public.coffee_sale_prices from anon, authenticated;" in text
    assert "grant " not in text


def test_tables_have_the_ledger_columns(sql):
    assert columns(sql, "farmers") == {"id", "name", "pin_hash", "region", "lat", "lon", "is_synthetic"}
    assert columns(sql, "calls") == {"id", "farmer_id", "received_at", "language", "audio_path",
                                     "transcript_sw", "transcript_en", "is_synthetic"}
    assert columns(sql, "entries") == {"id", "call_id", "farmer_id", *ENTRY_FIELDS}


def test_row_level_security_is_on_for_every_table(sql):
    for table in ("farmers", "calls", "entries"):
        assert f"alter table public.{table} enable row level security;" in sql
    assert "create policy" not in sql


def test_migration_version_matches_remote_name():
    """The version is already applied live; renaming the file would break `supabase db push`."""
    (path,) = MIGRATIONS.glob("*_ledger_tables.sql")
    assert path.name == "20261003234752_ledger_tables.sql"


def test_applied_migration_is_unchanged(sql):
    """`supabase db push` never re-runs an applied version, so editing this file would silently
    split the repo from the live database. Schema changes go into a new, additive migration."""
    digest = hashlib.sha256(normalised(sql).encode()).hexdigest()
    assert digest == APPLIED_LEDGER_SQL_SHA256, "20261003234752 is live: add a new migration instead"


def test_every_migrated_table_keeps_row_level_security_without_policies():
    """Only the server may read or write; the anon and publishable keys must see nothing."""
    text = all_migrations()
    created = set(re.findall(r"create table (?:if not exists )?(?:public\.)?(\w+)", text))
    secured = set(re.findall(r"alter table (?:public\.)?(\w+) enable row level security", text))
    assert {"farmers", "calls", "entries"} <= created
    assert created - secured == set(), "every new table needs `enable row level security`"
    assert "create policy" not in text
    assert "disable row level security" not in text


def test_deleting_a_farmer_or_call_never_cascades():
    """The synthetic reset (#20) relies on this: deleting a farmer or call that real rows
    point at must fail, not take those rows with it (or orphan them)."""
    assert re.findall(r"on delete (cascade|set null|set default)", all_migrations()) == []


# --- Regression tests from review (#42): the Uganda migration must stay additive and keep its contract. ---

COFFEE_SALE_PRICES_COLUMNS = [
    "entry_id", "farmer_id", "is_synthetic", "coffee_form", "coffee_type", "sale_date", "amount_kg",
    "price_total", "ugx_per_kg", "village_id", "region", "district", "sub_county", "parish", "village"]


def later_migrations():
    """Each migration after the live ledger one, comments removed."""
    paths = sorted(MIGRATIONS.glob("*.sql"))
    return {p.name: re.sub(r"--[^\n]*", "", p.read_text()).lower() for p in paths if p.name > paths[0].name}


def test_later_migrations_never_drop_or_rewrite_live_data():
    """40/416/511 live rows must survive: no drops, truncates, deletes, renames or type changes."""
    destructive = r"drop (table|column|view|schema)|truncate|delete from|rename |alter column \w+ (set data )?type"
    for name, text in later_migrations().items():
        assert re.findall(destructive, text) == [], name
        for constraint in re.findall(r"drop constraint (?:if exists )?(\w+)", text):
            assert f"add constraint {constraint} " in text, f"{name}: {constraint} dropped, not re-added"


def test_check_swaps_keep_every_value_old_rows_may_hold():
    """A re-added CHECK may only widen its list (the currency swap must keep KES and USD)."""
    every = re.findall(r"check\s*\(\s*(\w+)\s+in\s*\(([^)]*)\)\)", uncommented_sql())
    first = {}
    for column, values in every:
        first.setdefault(column, set(re.findall(r"'([^']*)'", values)))
    for column, latest in check_lists().items():
        assert first[column] <= set(latest), column
    assert {"KES", "UGX", "USD", "other"} <= set(check_lists()["currency"])


def top_level_items(select_list):
    """Split a select list on commas that are not inside parentheses."""
    items, depth, start = [], 0, 0
    for i, ch in enumerate(select_list):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            items, start = [*items, select_list[start:i]], i + 1
    return [*items, select_list[start:]]


def test_coffee_sale_prices_columns_match_contract():
    """#43 reads these columns by name; the view must never expose pin_hash or other farmer fields."""
    text = uncommented_sql()
    select = re.search(r"create view public\.coffee_sale_prices .*? as\s+select (.*?)\s+from ", text, re.S).group(1)
    names = [re.split(r"[\s.]", item.strip())[-1] for item in top_level_items(select)]
    assert names == COFFEE_SALE_PRICES_COLUMNS
    assert "pin_hash" not in select


def test_farmer_id_becomes_nullable_on_calls_and_entries():
    """Unidentified callers (#11) get a call row and entries before a farmer is known."""
    text = uncommented_sql()
    for table in ("calls", "entries"):
        alters = " ".join(m.group(1) for m in re.finditer(rf"alter table public\.{table}\b(.*?);", text, re.S))
        assert re.search(r"alter column farmer_id drop not null", alters), table


def test_calls_pending_index_is_partial_on_unprocessed():
    assert re.search(r"create index calls_pending_idx on public\.calls \(status\) where status <> 'processed';",
                     uncommented_sql())
