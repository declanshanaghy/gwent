import os
import hashlib
import json
import jsonschema
import logging

KIND = 'kind'
SUBKIND = 'subkind'
CONTENT_ID = 'content_id'


class InvalidSubkind(Exception):
    pass


class Message(object):
    _schema = None
    instance = None

    def __init__(self, instance, subkind=None):
        self._log = logging.getLogger(
            f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.instance = instance
        self.instance[KIND] = self.kind

        if subkind is not None:
            self.instance[SUBKIND] = subkind

        if self.should_validate():
            self.validate()

    def __str__(self):
        return self.instance

    def get_schema(self):
        if self._schema is None:
            top = os.path.abspath(os.path.dirname(__file__))
            abs_schema = os.path.join(top, f'{self.kind}_schema.json')
            with open(abs_schema) as fd:
                self._schema = json.load(fd)
        return self._schema

    def should_validate(self):
        return True

    def validate(self):
        jsonschema.validate(instance=self.instance, schema=self.get_schema())
        self.validate_xtra()

    def validate_xtra(self):
        pass

    @property
    def body(self):
        kwargs = self._ensure_content_id()
        content_with_id = json.dumps(self.instance, **kwargs).strip()
        return content_with_id

    @property
    def body_pretty(self):
        self._ensure_content_id()
        return json.dumps(self.instance, sort_keys=True, indent=4).strip()

    @property
    def content_id(self):
        self._ensure_content_id()
        return self.instance[CONTENT_ID]

    def _ensure_content_id(self):
        kwargs = {
            'sort_keys': True,
            'indent': None,
            'separators': (',', ':')
        }
        content = json.dumps(self.instance, **kwargs).strip()
        cid = hashlib.md5(content.encode()).hexdigest()
        self.instance[CONTENT_ID] = cid
        return kwargs


    @property
    def kind(self):
        raise NotImplementedError(
            f'{self.__class__} must implement kind property')

    @property
    def subkind(self):
        return self.instance.get(SUBKIND)

    @property
    def announcement(self):
        raise NotImplementedError(
            f'{self.__class__} must implement speech property')
