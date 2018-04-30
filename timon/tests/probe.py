from timon.probes import Probe


class TestProbe(Probe):
    def __init__(self, **kwargs):
        print("CREATE PROBE %s" % kwargs)
        self.tst_results = kwargs.get('tst_results')
        print("rslts", self.tst_results)
        for key in list(kwargs.keys()):
            # drop all keys with a tst_prefix
            if key.startswith("tst"):
                kwargs.pop(key)
        super().__init__(**kwargs)

    async def probe_action(self):
        idx = 0
        self.status = self.tst_results[idx]
        self.msg = "test probe msg %d" % idx
