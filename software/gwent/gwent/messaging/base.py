import os
import hashlib
import json
import jsonschema
import logging


KIND = 'kind'


class Message(object):
    _schema = None
    instance = None

    def __init__(self, instance):
        self._log = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.instance = instance
        self.instance[KIND] = self.kind

        if self.should_validate():
            self.validate()

    def __str__(self):
        return self.instance

    def get_schema(self):
        if self._schema is None:
            top = os.path.abspath(os.path.dirname(__file__))
            mod, = self.__class__.__module__.split('.')[2:3]
            abs_schema = os.path.join(top, mod, f'schema_{self.kind}.json')
            with open(abs_schema) as fd:
                self._schema = json.load(fd)
        return self._schema

    def should_validate(self):
        return True

    def validate(self):
        self._log.debug({
            'action': 'validate',
            'kind': self.kind,
        })
        jsonschema.validate(instance=self.instance, schema=self.get_schema())
        self.validate_xtra()

    def validate_xtra(self):
        pass

    @property
    def body(self):
        return json.dumps(self.instance, sort_keys=True, indent=None,
                          separators=(',', ':')).strip()

    @property
    def body_pretty(self):
        return json.dumps(self.instance, sort_keys=True, indent=4).strip()

    @property
    def content_id(self):
        return hashlib.md5(self.body.encode()).hexdigest()

    @property
    def kind(self):
        raise NotImplementedError(f'{self.__class__} must implement kind property')

    @property
    def speech(self):
        raise NotImplementedError(f'{self.__class__} must implement speech property')
