"""Additive schema for the isolated cloud candidate, not the existing Originals table."""
from cloud.client import ACCOUNTS, BUDGETS, RECORDS


def table_creation(spec):
    # Inline table creation uses "attributes" for indexes; the separate
    # create-index endpoint and returned index model use "columns".
    # Encrypted columns are created through their dedicated endpoint because
    # inline creation on the hosted service did not retain encrypt=True.
    return {**spec, 'columns': [c for c in spec['columns'] if not c.get('encrypt')], 'indexes': [
        {**{key: value for key, value in index.items() if key != 'columns'},
         'attributes': list(index['columns'])} for index in spec['indexes']]}


def column(key, type, **extra):
    return {'key': key, 'type': type, 'required': True, **extra}


TABLES = [
    {'tableId': ACCOUNTS, 'name': 'Ditto private accounts v2', 'columns': [
        column('email', 'varchar', size=254), column('display_name', 'varchar', size=128),
        column('salt', 'varchar', size=64), column('password_hash', 'varchar', size=64),
        column('verified', 'boolean'), column('closing', 'boolean'),
        column('auth_epoch', 'integer'), column('reset_generation', 'integer'), column('revision', 'integer'),
    ], 'indexes': [{'key': 'email_unique', 'type': 'unique', 'columns': ['email'], 'orders': ['ASC']}]},
    {'tableId': RECORDS, 'name': 'Ditto private records v2', 'columns': [
        column('owner_id', 'varchar', size=36), column('kind', 'varchar', size=32),
        column('parent_id', 'varchar', size=64), column('state', 'varchar', size=32),
        column('payload', 'mediumtext', encrypt=True), column('revision', 'integer'),
        column('expires_at', 'datetime', required=False),
    ], 'indexes': [
        {'key': 'owner_kind', 'type': 'key', 'columns': ['owner_id', 'kind'], 'orders': ['ASC', 'ASC']},
        {'key': 'owner_kind_state', 'type': 'key', 'columns': ['owner_id', 'kind', 'state'], 'orders': ['ASC'] * 3},
        {'key': 'owner_kind_parent', 'type': 'key', 'columns': ['owner_id', 'kind', 'parent_id'], 'orders': ['ASC'] * 3},
        {'key': 'job_due', 'type': 'key', 'columns': ['kind', 'state', 'expires_at'], 'orders': ['ASC'] * 3},
    ]},
    {'tableId': BUDGETS, 'name': 'Ditto private request budgets v2', 'columns': [
        column('count', 'integer'), column('expires_at', 'datetime'),
    ], 'indexes': [{'key': 'budget_expiry', 'type': 'key', 'columns': ['expires_at'], 'orders': ['ASC']}]},
]
