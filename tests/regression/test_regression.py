import json
import os
from pathlib import Path
from typing import Optional

from docdeid import Annotation, AnnotationSet

from deduce import Deduce

_BASE_PATH = Path(os.path.dirname(__file__)).parent


def regression_test(
    model: Deduce,
    examples_file: str,
    enabled: set[str],
    known_failures: Optional[set[int]] = None,
):
    if known_failures is None:
        known_failures = set()

    common_path_str = str(_BASE_PATH) + str(examples_file)
    normalised_path = os.path.normpath(common_path_str)
    with open(normalised_path, "rb") as file:
        examples = json.load(file)["examples"]

    failures = set()

    for example in examples:
        trues = AnnotationSet(
            Annotation(**annotation) for annotation in example["annotations"]
        )
        preds = model.deidentify(text=example["text"], enabled=enabled).annotations

        try:
            assert trues == preds
        except AssertionError:
            failures.add(example["id"])

    assert failures == known_failures


def annotators_from_group(model: Deduce, group: str) -> set[str]:
    return {name for name, _ in model.processors[group]}.union({group})


class TestRegression:
    def test_regression_name(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/names.json",
            enabled=annotators_from_group(model, "names"),
        )

    def test_regression_location(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/locations.json",
            enabled=annotators_from_group(model, "locations"),
        )

    def test_regression_institution(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/institutions.json",
            enabled=annotators_from_group(model, "institutions"),
        )

    def test_regression_date(self, model):
        enabled_annotator_names = annotators_from_group(model, "dates")
        post_processing_annotators = annotators_from_group(model, "post_processing")
        enabled_annotator_names = enabled_annotator_names.union(post_processing_annotators)
        regression_test(
            model=model,
            examples_file="./data/regression_cases/dates.json",
            enabled=enabled_annotator_names,
        )

    def test_regression_age(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/ages.json",
            enabled=annotators_from_group(model, "ages"),
        )

    def test_regression_identifier(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/identifiers.json",
            enabled=annotators_from_group(model, "identifiers"),
        )

    def test_regression_phone(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/phone_numbers.json",
            enabled=annotators_from_group(model, "phone_numbers"),
        )

    def test_regression_email(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/emails.json",
            enabled=annotators_from_group(model, "email_addresses"),
        )

    def test_regression_url(self, model):
        regression_test(
            model=model,
            examples_file="./data/regression_cases/urls.json",
            enabled=annotators_from_group(model, "urls"),
        )
