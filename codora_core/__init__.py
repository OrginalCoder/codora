import sys
import django.template.context

if sys.version_info >= (3, 14):
    def _base_context_copy(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    django.template.context.BaseContext.__copy__ = _base_context_copy
