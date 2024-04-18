import docdeid as dd

from deduce.person import Person

text = (
    "betreft: Jan Jansen, bsn 111222333, patnr 000334433. De patient J. Jansen is 64 "
    "jaar oud en woonachtig in Utrecht. Hij werd op 10 oktober 2018 door arts "
    "Peter de Visser ontslagen van de kliniek van het UMCU. Voor nazorg kan hij "
    "worden bereikt via j.JNSEN.123@gmail.com of (06)12345678."
)


class TestDeduce:
    def test_annotate(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        doc = model.deidentify(text, metadata=metadata)
        doc.annotations.sorted(by=("start_char",))

        expected_annotations = dd.AnnotationSet(
            [
                dd.Annotation(
                    text="(06)12345678",
                    start_char=272,
                    end_char=284,
                    tag="telefoonnummer",
                ),
                dd.Annotation(text="111222333", start_char=25, end_char=34, tag="bsn"),
                dd.Annotation(
                    text="Peter de Visser", start_char=153, end_char=168, tag="persoon"
                ),
                dd.Annotation(
                    text="j.JNSEN.123@gmail.com",
                    start_char=247,
                    end_char=268,
                    tag="emailadres",
                ),
                dd.Annotation(
                    text="J. Jansen", start_char=64, end_char=73, tag="patient"
                ),
                dd.Annotation(
                    text="Jan Jansen", start_char=9, end_char=19, tag="patient"
                ),
                dd.Annotation(
                    text="10 oktober 2018", start_char=127, end_char=142, tag="datum"
                ),
                dd.Annotation(text="64", start_char=77, end_char=79, tag="leeftijd"),
                dd.Annotation(text="000334433", start_char=42, end_char=51, tag="id"),
                dd.Annotation(
                    text="Utrecht", start_char=106, end_char=113, tag="locatie"
                ),
                dd.Annotation(
                    text="UMCU", start_char=202, end_char=206, tag="ziekenhuis"
                ),
                dd.Annotation(
                    text="oud", start_char=85, end_char=88, tag="persoon"
                ),
            ]
        )

        doc.annotations = doc.annotations.sorted(by=("start_char",))
        expected_annotations = expected_annotations.sorted(by=("start_char",))
        assert doc.annotations == expected_annotations

    def test_deidentify(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        doc = model.deidentify(text, metadata=metadata)

        expected_deidentified = (
            "betreft: [PATIENT], bsn [BSN-1], patnr [ID-1]. De patient [PATIENT] is "
            "[LEEFTIJD-1] jaar [PERSOON-1] en woonachtig in [LOCATIE-1]. Hij werd op "
            "[DATUM-1] door arts [PERSOON-2] ontslagen van de kliniek van het "
            "[ZIEKENHUIS-1]. Voor nazorg kan hij worden bereikt via [EMAILADRES-1] "
            "of [TELEFOONNUMMER-1]."
        )

        assert doc.deidentified_text == expected_deidentified

    def test_annotate_intext(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        doc = model.deidentify(text, metadata=metadata)

        expected_intext_annotated = (
            "betreft: <PATIENT>Jan Jansen</PATIENT>, bsn <BSN>111222333</BSN>, "
            "patnr <ID>000334433</ID>. De patient <PATIENT>J. Jansen</PATIENT> is "
            "<LEEFTIJD>64</LEEFTIJD> jaar <PERSOON>oud</PERSOON> en woonachtig in <LOCATIE>Utrecht"
            "</LOCATIE>. Hij werd op <DATUM>10 oktober 2018</DATUM> door arts "
            "<PERSOON>Peter de Visser</PERSOON> ontslagen van de kliniek van het "
            "<ZIEKENHUIS>UMCU</ZIEKENHUIS>. Voor nazorg kan hij worden bereikt "
            "via <EMAILADRES>j.JNSEN.123@gmail.com</EMAILADRES> of "
            "<TELEFOONNUMMER>(06)12345678</TELEFOONNUMMER>."
        )

        assert dd.utils.annotate_intext(doc) == expected_intext_annotated

    def test_deidentify_location_with_space(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        text_with_location = ("betreft: Jan Jansen, bsn 111222333, patnr 000334433. De patient J. Jansen is 64 "
                              "jaar oud en woonachtig in Utrecht, Adres Oude Turfmarkt.")
        doc = model.deidentify(text_with_location, metadata=metadata)

        expected_deidentified = (
            "betreft: [PATIENT], bsn [BSN-1], patnr [ID-1]. De patient [PATIENT] is "
            "[LEEFTIJD-1] jaar [PERSOON-1] en woonachtig in [LOCATIE-1], Adres Oude Turfmarkt."
        )

        assert doc.deidentified_text == expected_deidentified

    def test_deidentify_placenames(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        text_with_location = ("betreft: Jan Jansen, bsn 111222333, patnr 000334433. De patient J. Jansen is 64 "
                              "jaar oud en woonachtig in utrecht, UTrecht, zaltbommel, bunNIK, Halfweg, Helfweg, "
                              "Súdwest-Fryslân, Alphen ( NB ), Alphen (ZH)")
        doc = model.deidentify(text_with_location, metadata=metadata)

        expected_deidentified = (
            "betreft: [PATIENT], bsn [BSN-1], patnr [ID-1]. De patient [PATIENT] is "
            "[LEEFTIJD-1] jaar [PERSOON-1] en woonachtig in [LOCATIE-1], [LOCATIE-2], [LOCATIE-3], [LOCATIE-4], "
            "[LOCATIE-5], Helfweg, [LOCATIE-6], [LOCATIE-7], [LOCATIE-8] (ZH)"
        )

        assert doc.deidentified_text == expected_deidentified

    def test_deidentify_streetnames(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        text_with_location = ("betreft: Jan Jansen, bsn 111222333, patnr 000334433. De patient J. Jansen is 64 "
                              "jaar oud en woonachtig in Dorpstraat 1, DORPSTRAAT 2, DorpStraat 3, dorpstraat 4, "
                              "Dorpstraat 6, Amsterdamsestraatweg, 1234 AA, 1e Achterstraat, "
                              "Amsterdamsestraatweg")

        doc = model.deidentify(text_with_location, metadata=metadata)

        expected_deidentified = (
            "betreft: [PATIENT], bsn [BSN-1], patnr [ID-1]. De patient [PATIENT] is [LEEFTIJD-1] jaar [PERSOON-1] en "
            "woonachtig in [LOCATIE-1], [LOCATIE-2], [LOCATIE-3], [LOCATIE-4], [LOCATIE-1], Amsterdamsestraatweg, "
            "[LOCATIE-5], 1e Achterstraat, Amsterdamsestraatweg"
        )

        assert doc.deidentified_text == expected_deidentified

    def test_deidentify_careinstitutes(self, model):
        metadata = {"patient": Person(first_names=["Jan"], surname="Jansen")}
        text_with_location = ("betreft: Jan Jansen, bsn 111222333, patnr 000334433. De patient J. Jansen is 64 "
                              "jaar oud en opgenomen in ggzingeest, daarna in reade. Hij haalt zijn medicatie"
                              "bij Rijn apotheek of 'Rijn apotheek'")
        # TODO 1 problem remains to be solved with streetnames:
        # 1) Streetnames without a house number are not masked
        #    e.g. '... Amsterdamsestraatweg, 1234 AA ...' and 'Amsterdamsestraatweg' is not picked up

        doc = model.deidentify(text_with_location, metadata=metadata)

        expected_deidentified = (
            "betreft: [PATIENT], bsn [BSN-1], patnr [ID-1]. De patient [PATIENT] is [LEEFTIJD-1] jaar [PERSOON-1] en"
            " opgenomen in [ZORGINSTELLING-1], daarna in [ZORGINSTELLING-2]. Hij haalt zijn medicatie"
            "bij [ZORGINSTELLING-3] of '[ZORGINSTELLING-3]'"
        )

        assert doc.deidentified_text == expected_deidentified

    def test_streetname_without_housenumber(self, model):
        metadata = {"patient": Person(first_names=["Fien"], surname="Jansen")}
        text_with_location = ("Mevrouw van der Heide-Jagers Op Akkerhuis werd opgenomen op 15 mei")

        doc = model.deidentify(text_with_location, metadata=metadata)

        expected_deidentified = (
            "[PERSOON-1] werd AAopgenomen op [DATUM-1]"
        )

        assert doc.deidentified_text == expected_deidentified