from django.test import TestCase
from mediabrowser.models import VisionItem, Genre, Keyword, Person
from scripts.populate_db import PopulateDatabase
from pathlib import Path
import unittest


class VisionModelTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.p = Path(__file__).parent.joinpath("data")

        pop_db = PopulateDatabase(quiet=True)
        films_txt = cls.p.joinpath("films.txt")
        patch_csv = cls.p.joinpath("patch.csv")
        print()
        pop_db.populate(films_txt, patch_csv)

    def test_populate_db(self):
        # check that PopulateDatabase worked as expected
        for model_class in [VisionItem, Genre, Person]:
            items = model_class.objects.all()
            self.assertGreater(len(items), 0)

            if model_class == VisionItem:
                self.assertEqual(len(items), 10)

        # Keyword seems to have disappeared when getting from imdb
        self.assertEqual(len(Keyword.objects.all()), 0)

        with open(self.p.joinpath("expected.csv")) as fileobj:
            text = fileobj.read()

        expected = {}
        header, *lines = [line for line in text.split("\n") if line]
        _, *header = header.split("\t")  # first is 'filename'
        for line in lines:
            fname, *data = line.split("\t")
            expected[fname] = dict(zip(header, data))

        int_types = ["year", "runtime", "imdb_id"]
        bool_types = ["colour"]
        type_map = {name: int for name in int_types}
        type_map.update({name: bool for name in bool_types})

        for fname, exp_dct in expected.items():
            item = VisionItem.objects.get(filename=fname)
            for key, exp_value in exp_dct.items():
                t = type_map.get(key, None)
                if t is not None:
                    exp_value = t(exp_value)
                db_value = getattr(item, key)
                fail_msg = f"{fname} '{key}' expected {exp_value} got {db_value}"
                self.assertEqual(db_value, exp_value, fail_msg)

    @unittest.skip("not written yet")
    def test_aliases(self):
        # check that can add aliases for people and query
        ...
