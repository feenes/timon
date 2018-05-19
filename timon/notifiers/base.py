from minibelt import import_from_path
import logging


# cache of notifiers
notifiers = {}

logger = None


class Notifier:
    def __init__(self, **kwargs):
        global logger
        kwargs.pop('cls', None)  # get rid of cls
        logger = logger if logger else logging.getLogger(__name__)
        print("CREATE A NOTIFIER")
        notify_states = ["WARNING", "ERROR"]
        notify_states = list(kwargs.pop('notify_states', [])) or notify_states
        self.name = kwargs.pop('name', None)
        self.users = kwargs.pop('users', [])
        self.notify_states = notify_states
        if kwargs:
            logger.warning("unused kwargs for notifier: %s", kwargs.keys())

    def shall_notify(self, probe, probe_state):
        status = probe_state[-1][1]
        rslt = status in self.notify_states
        return rslt

    async def notify(self, probe, probe_state):
        status = probe_state[-1][1]
        print("#### NOTIFY ####", probe.name, status, self.users)


def get_notifier_cls(cls_name):
    notifiers[cls_name] = notifier = (
        notifiers.get(cls_name) or import_from_path(cls_name))
    return notifier


def mk_notifier(cls_name, *args, **kwargs):
    """ creates a probe instance """
    notifier = get_notifier_cls(cls_name)
    return notifier(*args, **kwargs)
