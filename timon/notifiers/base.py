class Notifier:
    def __init__(self, **kwargs):
        notify_states = ["WARNING", "ERROR"]
        self.notify_states = notify_states

    def shall_notify(self, state):
        return state in self.notify_states

    async def notify(self, state):
        print("#### NOTIFY ####", state)
