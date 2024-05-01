import csv
import logging
import multiprocessing
import sys
from typing import Optional

import deduce
import numpy
from deduce.person import Person
from deduce_model import initialize_deduce
from examples import example_text, example_texts
from flask import Flask, abort, request
from flask_restx import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(
    app,
    title="Deduce Web Service",
    description=f"API to de-identify text using Deduce v{deduce.__version__}",
)
api.logger.setLevel(logging.INFO)


class NullableString(fields.String):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "nullable string"


payload_model = api.model(
    "payload",
    {
        "text": NullableString(example=example_text["text"], required=True),
        "patient_first_names": fields.String(
            example=example_text["patient_first_names"],
            description="Multiple names can be separated by white space",
        ),
        "patient_surname": fields.String(example=example_text["patient_surname"]),
        "id": fields.String(example=example_text["id"], required=False),
        "disabled": fields.List(
            fields.String(), example=example_text["disabled"], required=False
        ),
    },
)

response_model = api.model(
    "response", {"text": fields.String, "id": fields.String(required=False)}
)

payload_model_bulk = api.model(
    "payloadbulk",
    {
        "texts": fields.List(
            fields.Nested(payload_model),
            example=example_texts["texts"],
            required=True,
        ),
        "disabled": fields.List(
            fields.String(), example=example_texts["disabled"], required=False
        ),
    },
)

response_model_bulk = api.model(
    "responsebulk", {"texts": fields.List(fields.Nested(response_model))}
)


@api.route("/deidentify")
class DeIdentify(Resource):
    @api.expect(payload_model, validate=True)
    @api.marshal_with(response_model)
    def post(self):

        data = request.get_json()

        if data["text"] is None:
            return format_result(data, output_text=None)

        return annotate_text(data)


@api.route("/deidentify_bulk")
class DeIdentifyBulk(Resource):
    @api.expect(payload_model_bulk, validate=True)
    @api.marshal_list_with(response_model_bulk)
    def post(self):

        data = request.get_json()
        num_texts = len(data["texts"])

        if "disabled" in data:
            for record in data["texts"]:
                record["disabled"] = data["disabled"]

        api.logger.info(
            f"Received {num_texts} texts in " f"deidentify_bulk, starting to process..."
        )

        response = annotate_text_bulk(request.get_json()["texts"])

        api.logger.info(f"Done processing {num_texts} texts.")

        return response


def format_result(input_data: dict, output_text: Optional[str]) -> dict:

    result = {"text": output_text}

    if input_data.get("id", None):
        result["id"] = input_data["id"]

    return result


def deidentify_tab_delimited_file(deduce_model, path_to_file, target_output_stream):
    """
    Reads a tab-delimited file with the column format defined below in the covert_line method and outputs the
    deidentified text to the specified standard output.
    """
    # see https://stackoverflow.com/questions/15063936/csv-error-field-larger-than-field-limit-131072 for the rationale
    # of the lines below
    ii32 = numpy.iinfo(numpy.int32)
    new_limit = numpy.intc(ii32.max) - 1
    csv.field_size_limit(int (new_limit))
    with open(path_to_file, closefd=True, encoding="UTF-8") as input_file:
        tsv_reader = csv.reader(input_file, delimiter='\t')
        line_number = 0
        print("\n")
        for line in tsv_reader:
            data = convert_line(line)
            line_number += 1
            deidentified_text = deduce_model.deidentify(data)
            line.append(deidentified_text.get('text'))
            if target_output_stream is None:
                print("\t".join(line))
            else:
                print("\t".join(line), file=target_output_stream)
    # closing file not needed because we use a with open construct.


def convert_line(column_value_list):
    """
    Converts a tab-delimited line (UTF-8) to JSON-format as defined in the api.model.
    """
    # TODO Consider introducing an abstract base class (ABC) or a formal or informal interface
    # to allow the deduce_app to work with difference data sources. Two implementations are thinkable: the current
    # web-service REST-interface using flask and a stream from a delimited file. This method should be incorporated
    # in the interface / ABC. The current version of the method assumes the following columns:
    # 0) PATIENT_HASH
    # 1) NOTE_ID
    # 2) NOTE_CATEGORY
    # 3) FIRST_NAME
    # 4) INITIALS
    # 5) FAMILY_NAME
    # 6) CAPITAL_NAME
    # 7) FAMILY_NAME_2
    # 8) NOTE_TEXT
    #
    # A final implementation can include a dict to map the columns in the text-line to the deduce data

    data = {
        "text": column_value_list[8],
        "patient_surname_2": column_value_list[7],
        "patient_surname_capitals": column_value_list[6],
        "patient_surname": column_value_list[5],
        "patient_initials": column_value_list[4],
        "patient_first_names": column_value_list[3],
        "note_cat": column_value_list[2],
        "note_id": column_value_list[1],
        "hash_id": column_value_list[0],
        "disabled": [],
    }
    return data


def annotate_text(data):
    """
    Run a single text through the Deduce pipeline
    """

    deduce_args = {"text": data["text"]}

    if ("patient_first_names" in data) or ("patient_surname" in data):
        deduce_args["metadata"] = dict()
        deduce_args["metadata"]["patient"] = Person.from_keywords(
            patient_first_names=data.get("patient_first_names", None),
            patient_surname=data.get("patient_surname", None),
            patient_initials=data.get("patient_initials", None),
            patient_given_name=data.get("patient_given_name", None)
        )

    if data.get("disabled", None):
        deduce_args["disabled"] = set(data["disabled"])

    try:
        doc = deduce_model.deidentify(**deduce_args)
    except (
        AttributeError,
        IndexError,
        KeyError,
        MemoryError,
        NameError,
        OverflowError,
        RecursionError,
        RuntimeError,
        StopIteration,
        TypeError,
    ) as e:
        api.logger.exception(e)
        abort(
            500,
            f"Deduce encountered this error when processing a text: {e}. For full traceback, see logs.",
        )
        return

    return format_result(data, output_text=doc.deidentified_text)


def annotate_text_bulk(data):
    """
    Run multiple texts through the Deduce pipeline in parallel
    """
    with multiprocessing.Pool() as pool:
        result = pool.map(annotate_text, data)

    result = {"texts": result}
    return result


if __name__ == "__main__":
    app.run(port=5000)
