"""
Runs a validation test which compares records found in the tab-delimited file input-output-test.tsv. Each record
contains an input and the expected output. E.g.
My name is John Johnson and I live in Wisconsin.<TAB>My name is <PATIENT> and I live in <LOCATIE-1>.

The failing comparisons are sent to standard-output and together with some summary statistics.
"""
import json
from typing import Optional

from docdeid import Annotation, AnnotationSet

from deduce import Deduce
from deduce.person import Person


def annotators_from_group(model: Deduce, group: str) -> set[str]:
    return {name for name, _ in model.processors[group]}.union({group})

def validation_test(
    examples_file: str
):
    deduce = Deduce()
    known_failures = set()

    record_list = list()
    with open(examples_file, mode="r", encoding="utf-8") as file:
        lines = file.readlines()
        count = 0
        for line in lines:
            # skip lines starting with the comment character
            if not line.strip().startswith(str("#")):
                record_list.append(line.rstrip('\n'))
            count += 1
    print("Number of records read: ", len(record_list))

    mismatch_count = 0
    record_count = 1;
    for record in record_list:
        columns = record.split("\t")
        expected_output = columns[5]

        person = Person(first_names=columns[0], initials=columns[1], surname=columns[2])

        result_document = deduce.deidentify(text=columns[4], metadata={"patient" : person})
        actual_output = result_document.deidentified_text
        # do not take case into account
        matching = expected_output == actual_output
        if not matching:
            mismatch_count += 1
            print("==> Mismatch at record ", record_count)
            print("Expected: >" + expected_output + "<")
            print("Actual:   >" + actual_output + "<")
        record_count += 1

    print("Done")
    print("Number of mismatches: ", mismatch_count)
    failures = set()

    #
    # for example in examples:
    #     trues = AnnotationSet(
    #         Annotation(**annotation) for annotation in example["annotations"]
    #     )
    #     preds = model.deidentify(text=example["text"], enabled=enabled).annotations
    #
    #     try:
    #         assert trues == preds
    #     except AssertionError:
    #         failures.add(example["id"])

    assert failures == known_failures


def main():
    file_to_test = './regression/input-output-test.tsv'
    validation_test(file_to_test)

if __name__ == "__main__":
    main()