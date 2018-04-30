import os

from collections import defaultdict
from unittest.mock import MagicMock

mod_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
test_data_dir = os.path.join(mod_dir, 'data', 'test')


class Options:
    """ options for testing """
    def __init__(self, fname, **kwargs):
        self.check = False
        self.workdir = ""
        self.fname = fname
        self.shell_loop = False
        self.loop = False
        self.probe = None
        self.force = None
        self.statefile = None
        for key, val in kwargs.items():
            setattr(self, key, val)


class Writer(MagicMock):
    written = defaultdict(list)

    def __init__(self, *args, **kwargs):
        fname = args[0]
        super().__init__(*args, **kwargs)
        self.fname = fname

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    @classmethod
    def written_data(cls, fname=None):
        if fname is None:
            fnames = list(cls.written.keys())
            fname = fnames[0]
        return "".join(cls.written[fname])

    def write(self, data):
        self.written[self.fname].append(data)

    @classmethod
    def clear_written(cls):
        cls.written.clear()
