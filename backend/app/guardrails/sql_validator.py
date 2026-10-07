"""Validate LLM-generated SQL before it can touch the database.

Defense in depth: this parser-level check is backed by the `query_ro` role
(SELECT on schema `data` only), a read-only transaction and a statement timeout.
"""
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError
from sqlglot.optimizer.qualify import qualify

ALLOWED_SCHEMA = "data"
DENY_FUNC_PREFIXES = ("pg_", "dblink", "lo_")
DENY_FUNCS = {
    "current_setting", "set_config", "query_to_xml", "table_to_xml", "query_to_xml_and_xmlschema",
    "version", "inet_server_addr", "inet_server_port", "txid_current", "current_user", "session_user",
    "current_database", "current_schema", "has_table_privilege",
}
_FORBIDDEN_NAMES = (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable", "Command", "Merge",
    "TruncateTable", "Into", "Lock", "Set", "Transaction", "Commit", "Rollback", "Grant", "Copy",
    "Use", "Pragma", "Cache", "Uncache", "Refresh", "Analyze",
)
FORBIDDEN_NODES = tuple(t for t in (getattr(exp, n, None) for n in _FORBIDDEN_NAMES) if isinstance(t, type))
_SET_OP_NAMES = ("SetOperation", "Union", "Except", "Intersect")
SET_OPS = tuple(t for t in (getattr(exp, n, None) for n in _SET_OP_NAMES) if isinstance(t, type))


class SQLValidationError(ValueError):
    pass


def _function_name(func: exp.Func) -> str:
    if isinstance(func, exp.Anonymous):
        return str(func.this).lower()
    return func.sql_name().lower()


def validate_sql(sql: str, schema: dict[str, dict[str, str]], max_rows: int) -> str:
    try:
        statements = [s for s in sqlglot.parse(sql or "", read="postgres") if s is not None]
    except (ParseError, SqlglotError) as exc:
        raise SQLValidationError(f"SQL could not be parsed: {exc}") from exc
    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, *SET_OPS)):
        raise SQLValidationError("Only SELECT queries are allowed.")

    for node in tree.find_all(exp.Expression):
        if isinstance(node, FORBIDDEN_NODES):
            raise SQLValidationError(f"Forbidden SQL construct: {type(node).__name__}.")

    for func in tree.find_all(exp.Func):
        name = _function_name(func)
        if name.startswith(DENY_FUNC_PREFIXES) or name in DENY_FUNCS:
            raise SQLValidationError(f"Function '{name}' is not allowed.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = (table.name or "").lower()
        db = (table.db or "").lower()
        if table.args.get("catalog"):
            raise SQLValidationError("Cross-database references are not allowed.")
        if not db and name in cte_names:
            continue
        if db and db != ALLOWED_SCHEMA:
            raise SQLValidationError(f"Access to schema '{db}' is not allowed. Use tables in schema 'data' only.")
        if name not in schema:
            available = ", ".join(sorted(schema)) or "(none)"
            raise SQLValidationError(f"Unknown table '{name or table.sql()}'. Available tables: {available}.")
        if not db:
            table.set("db", exp.to_identifier(ALLOWED_SCHEMA))

    try:
        qualify(
            tree.copy(),
            db=ALLOWED_SCHEMA,
            schema={ALLOWED_SCHEMA: {t: dict(cols) for t, cols in schema.items()}},
            dialect="postgres",
            validate_qualify_columns=True,
            quote_identifiers=False,
            identify=False,
        )
    except SqlglotError as exc:
        raise SQLValidationError(f"Column validation failed: {exc}") from exc

    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(max_rows)
    else:
        value = limit.args.get("expression")
        if not isinstance(value, exp.Literal) or value.is_string:
            raise SQLValidationError("LIMIT must be a plain number.")
        if int(value.this) > max_rows:
            tree.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return tree.sql(dialect="postgres")
