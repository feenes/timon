from timon.notifiers import Notifier


def default_callback(*args, **kwargs):
    print("I got called with %r %r" % (args, kwargs))


class TestNotifier(Notifier):
    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback or default_callback

    async def notify(self, state):
        print("#### NOTIFY %s with callback %s"
              % (state, self.callback))
        self.callback(self, state)
