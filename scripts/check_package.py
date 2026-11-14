"""Check an installed nodestro-examples package: every template, language, part and sample file is there.

Run it with the interpreter of a fresh environment, outside the source checkout (CI does this for the
wheel), so the package data is read from the installed package and never from the repository.
"""

from __future__ import annotations

import sys

from nodestro_runtime.schemas import LANGUAGES

import nodestro_examples as examples
from nodestro_examples import samples


def main() -> int:
    location = examples.__file__
    if "site-packages" not in location:
        print(f"error: nodestro_examples is not installed but imported from {location}", file=sys.stderr)
        return 1
    ids = examples.template_ids()
    assert len(ids) == 25, ids
    built = 0
    for language in LANGUAGES:
        for template_id in ids:
            examples.detail(template_id, language)
            assert examples.agent_plan(template_id, language), template_id
            for part_id in examples.part_ids(template_id):
                examples.build_part(part_id, language)
            for sample_id in samples.sample_ids(template_id):
                _name, _media_type, data = samples.render(template_id, sample_id, language)
                assert data, (template_id, sample_id, language)
                built += 1
    # The evaluation set of the web research example (fixtures for the test search provider) is package data too.
    assert examples.evaluation_set("web-research").questions
    print(f"{examples.__name__} {examples.__version__}: {len(ids)} templates in {len(LANGUAGES)} languages, ", end="")
    print(f"{built} sample files built, format {examples.FORMAT_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
