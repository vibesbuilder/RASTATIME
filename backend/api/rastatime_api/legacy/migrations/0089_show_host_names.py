# pylint: disable=invalid-name
#
# RASTATIME 2026-11-24 - host names per show (operator Go option B,
# ARCHITECTURE 23.133).  "Hosts involved" was a number per show, so a person
# hosting two shows counted twice in Analytics -> People Involved.  The
# shows now get the names of their hosts out of one register of persons;
# a person counts once per year however many shows they host.
#
#   cc_person (new)
#     id, name (128, whitespace collapsed), created_at, updated_at
#     unique on lower(name): one name = one person; two people with the
#     same name are told apart in the name itself, e.g. "Alex Example (B)".
#   cc_show_person (new)
#     show_id -> cc_show ON DELETE CASCADE, person_id -> cc_person ON
#     DELETE CASCADE, sort_order; primary key (show_id, person_id)
#
# cc_show_archiving.participants stays: a show without names keeps
# counting with its number, a show with names stores their count there.
# The readers check the tables first (information_schema), so code and
# migration may come in any order.  Propel is not regenerated.

from django.db import migrations

from ._migrations import legacy_migration_factory

UP = """
SET LOCAL lock_timeout = '5s';
CREATE TABLE cc_person (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX cc_person_name_key ON cc_person (lower(name));
CREATE TABLE cc_show_person (
    show_id INTEGER NOT NULL REFERENCES cc_show (id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES cc_person (id) ON DELETE CASCADE,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (show_id, person_id)
);
CREATE INDEX cc_show_person_person_id_idx ON cc_show_person (person_id);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("legacy", "0088_show_types"),
    ]
    operations = [
        migrations.RunPython(
            code=legacy_migration_factory(
                target="89",
                sql=UP,
            )
        )
    ]
