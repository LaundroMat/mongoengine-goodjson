#!/usr/bin/env python
# coding=utf-8

"""Follow Reference Field code."""

import mongoengine as db


class FollowReferenceField(db.ReferenceField):
    """
    Follow Reference Field.

    This field can be treated as a field like ReferenceField, but generates
    the JSON/dict of the referenced document like embedded document.

    Note:
        This field doesn't check recursion level. Therefore, please be careful
        for self-referenced document.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the class.

        Parameters:
            *args, **kwsrgs: Any arguments to be passed to ReferenceField.
        Keyword Arguments:
            id_check: Set False to disable id check. By default, this value is
                True
            autosave: Set True to save/update the referenced document when
                to_python is called.
        """
        self.id_check = kwargs.pop("id_check", True)
        self.autosave = kwargs.pop("autosave", False)
        super(FollowReferenceField, self).__init__(*args, **kwargs)

    def to_mongo(self, document, **kwargs):
        """
        Convert to python-typed dict.

        Parameters:
            document: The document.
        """
        ret = document
        if isinstance(document, db.Document):
            if document.pk is None and self.id_check:
                self.error("The referenced document needs ID.")
        else:
            ret = self.document_type.objects(
                pk=super(
                    FollowReferenceField, self
                ).to_mongo(document, **kwargs)
            ).get()
        return ret.to_mongo()

    def to_python(self, value):
        """
        Convert to python-based object.

        Parameters:
            value: The python-typed document.
        """
        ret = super(FollowReferenceField, self).to_python(value)
        if self.autosave:
            ret.save()
        return ret
