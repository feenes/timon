from minibelt import import_from_path


# cache of notifiers
notifiers = {}


class Notifier:
    def __init__(self, **kwargs):
        print("CREATE A NOTIFIER")
        notify_states = ["WARNING", "ERROR"]
        self.notify_states = notify_states

    def shall_notify(self, state):
        return state in self.notify_states

    async def notify(self, state):
        print("#### NOTIFY ####", state)


def get_notifier_cls(cls_name):
    notifiers[cls_name] = notifier = (
        notifiers.get(cls_name) or import_from_path(cls_name))
    return notifier


def mk_notifier(cls_name, *args, **kwargs):
    """ creates a probe instance """
    notifier = get_notifier_cls(cls_name)
    return notifier(*args, **kwargs)
