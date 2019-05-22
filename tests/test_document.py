#!/usr/bin/env python
# coding=utf-8

"""New Document serializer/deserializer."""

from unittest import TestCase

from bson import ObjectId
import mongoengine as db
from mongoengine_goodjson import GoodJSONEncoder, Document, EmbeddedDocument, DynamicDocument
from mongoengine_goodjson.document import Helper

try:
    from unittest.mock import patch, MagicMock, call
except ImportError:
    from mock import patch, MagicMock, call


class DocumentInhertCheck(TestCase):
    """Document, EmbeddedDocument and DynamicDocument should inhert Helper."""

    def test_document(self):
        """Document should inherit Helper."""
        self.assertTrue(issubclass(Document, Helper))

    def test_emb_document(self):
        """Embedded Document should inherit Helper."""
        self.assertTrue(issubclass(EmbeddedDocument, Helper))

    def test_dynamic_document(self):
        """Dynamic Document should inherit Helper."""
        self.assertTrue(issubclass(DynamicDocument, Helper))
        

class ToJSONTest(TestCase):
    """Good JSON Encoder invocation test."""

    def setUp(self):
        """Set up the class."""
        class SelfReferenceDocument(Document):
            name = db.StringField()
            reference = db.ReferenceField("self")

        class TestDocument(Document):
            title = db.StringField()
            references = db.ListField(
                db.ReferenceField(SelfReferenceDocument)
            )

        class TestDynamicDocument(DynamicDocument):
            title = db.StringField()
            references = db.ListField(
                db.ReferenceField(SelfReferenceDocument)
            )           
            
        self.references = [
            SelfReferenceDocument(
                pk=ObjectId(), name=("test {}").format(counter)
            ) for counter in range(3)
        ]
        for (index, srd) in enumerate(self.references):
            srd.reference = self.references[
                (index + 1) % len(self.references)
            ]
            srd.to_json = MagicMock(side_effect=srd.to_json)

        self.model_classes = [TestDocument, TestDynamicDocument]
        self.models = [
            TestDocument(pk=ObjectId(), title="Test", references=self.references),
            TestDynamicDocument(pk=ObjectId(), title="Test", references=self.references),
        ]
        
        for _model in self.model_classes:
            _model.to_mongo = MagicMock(
                return_value={
                    "id": _model.id,
                    "title": _model.title,
                    "references": self.references
                }
            )

    @patch("json.dumps")
    def test_document_types(self, dumps):
        """.to_json should call encode function."""
        for _model in self.models:
            _model.to_json()
            dumps.assert_called_once_with(
                _model.to_mongo(True), cls=GoodJSONEncoder
            )
            dumps.reset_mock()

    def test_followreference(self):
        """self.references.to_json should be called 3 times for each."""
               
        for _model in self.models:
            _model.to_json(follow_reference=True)
            for (index, reference) in enumerate(self.references):
                self.assertEqual(
                    reference.to_json.call_count, 3,
                    ("Reference {} should call to_json 3 times").format(index)
                )
                reference.to_json.assert_has_calls([
                    call(
                        cls=GoodJSONEncoder, follow_reference=True,
                        use_db_field=True, max_depth=3, current_depth=counter
                    ) for counter in range(1, 4)
                ], any_order=True)

    def test_followreference_max_15(self):
        """self.references.to_json should be called 15 times for each."""
        for _model in self.models:        
            _model.to_json(follow_reference=True, max_depth=15)
            for (index, reference) in enumerate(self.references):
                self.assertEqual(
                    reference.to_json.call_count, 15,
                    ("Reference {} should call to_json 15 times").format(index)
                )
                reference.to_json.assert_has_calls([
                    call(
                        cls=GoodJSONEncoder, follow_reference=True,
                        use_db_field=True, max_depth=15, current_depth=counter
                    ) for counter in range(1, 16)
                ], any_order=True)


class FromJSONTest(TestCase):
    """object hook generation invocation test."""

    def setUp(self):
        """Set up the class."""
        import json

        class TestDocument(Document):
            title = db.StringField()

        class TestDynamicDocument(DynamicDocument):
            title = db.StringField()
            
        self.model_classes = [TestDocument, TestDynamicDocument]
        self.data = json.dumps({"title": "Test"})
        
    @patch("mongoengine_goodjson.document.generate_object_hook")
    def test_document(self, hook_mock):
        """(Dynamic)Document.from_json should call generate_object_hook."""
        hook_mock.return_value = lambda x: {"title": "Test"}
        for _model_cls in self.model_classes:
            _model_cls.from_json(self.data)
            hook_mock.assert_called_once_with(_model_cls)
            hook_mock.reset_mock()
