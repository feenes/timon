from timon.probes import Probe


class TestProbe(Probe):
    def __init__(self, **kwargs):
        print("CREATE PROBE %s" % kwargs)
        self.tst_results = kwargs.get('tst_results') or ["OK"]
        print("rslts", id(self.tst_results), self.tst_results)
        for key in list(kwargs.keys()):
            # drop all keys with a tst_prefix
            if key.startswith("tst_"):
                kwargs.pop(key)
        super().__init__(**kwargs)

    async def probe_action(self):
        tst_results = self.tst_results
        self.status = tst_results[0]
        self.msg = "test probe msg"
        tst_results = tst_results[1:] + [tst_results[0]]
        print("change results to", id(tst_results), tst_results)
