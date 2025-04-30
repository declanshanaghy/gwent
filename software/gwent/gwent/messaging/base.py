import copy
import os
import hashlib
import json
import jsonschema

from gwent.utils.logging import get_logger

KIND = 'kind'
SUBKIND = 'subkind'
CONTENT_ID = 'content_id'


class InvalidSubkind(Exception):
    pass


class Message(object):
    _schema = None
    _instance = None

    def __init__(self, instance, subkind=None):
        self._log = get_logger(
            f'{self.__class__.__module__}.{self.__class__.__name__}')
        self._instance = instance
        self._instance[KIND] = self.kind

        if subkind is not None:
            self._instance[SUBKIND] = subkind

        if self.should_validate():
            self.validate()

    def __str__(self):
        return self._instance

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
        self._log.info(f"Validating message", {"instance": self._instance})
        jsonschema.validate(instance=self._instance, schema=self.get_schema())
        self.validate_extra()

    def validate_extra(self):
        pass

    def to_object(self):
        return copy.deepcopy(self._instance)
    
    @property
    def body(self):
        kwargs = self._ensure_content_id()
        content_with_id = json.dumps(self._instance, **kwargs).strip()
        return content_with_id

    @property
    def body_pretty(self):
        self._ensure_content_id()
        return json.dumps(self._instance, sort_keys=True, indent=4).strip()

    @property
    def content_id(self):
        self._ensure_content_id()
        return self._instance[CONTENT_ID]

    def _ensure_content_id(self):
        kwargs = {
            'sort_keys': True,
            'indent': None,
            'separators': (',', ':')
        }
        content = json.dumps(self._instance, **kwargs).strip()
        cid = hashlib.md5(content.encode()).hexdigest()
        self._instance[CONTENT_ID] = cid
        return kwargs


    @property
    def kind(self):
        raise NotImplementedError(
            f'{self.__class__} must implement kind property')

    @property
    def subkind(self):
        return self._instance.get(SUBKIND)

    @property
    def announcement(self):
        raise NotImplementedError(
            f'{self.__class__} must implement speech property')
