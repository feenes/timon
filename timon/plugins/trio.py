import trio
import trio_asyncio


val = 0


class Tracer(trio.abc.Instrument):
    def before_run(self):
        print("!!! run started")

    def _print_with_task(self, msg, task):
        # repr(task) is perhaps more useful than task.name in general,
        # but in context of a tutorial the extra noise is unhelpful.
        print("{}: {}".format(msg, task.name))

    def task_spawned(self, task):
        self._print_with_task("### new task spawned", task)

    def task_scheduled(self, task):
        self._print_with_task("### task scheduled", task)

    def before_task_step(self, task):
        self._print_with_task(">>> about to run one step of task", task)

    def after_task_step(self, task):
        self._print_with_task("<<< task step finished", task)

    def task_exited(self, task):
        self._print_with_task("### task exited", task)

    def before_io_wait(self, timeout):
        if timeout:
            print("### waiting for I/O for up to {} seconds".format(timeout))
        else:
            print("### doing a quick check for I/O")
        self._sleep_time = trio.current_time()

    def after_io_wait(self, timeout):
        duration = trio.current_time() - self._sleep_time
        print("### finished I/O check (took {} seconds)".format(duration))

    def after_run(self):
        print("!!! run finished")


async def trio_count():
    global val
    await trio.sleep(1)
    print("triocount", val)
    val += 1


async def async_main_wrapper(options, cfg, run_once, t00, run_func):
    print("R-once", run_once)
    async with trio_asyncio.open_loop() as loop:
        await trio_count()
        rslt = await loop.run_asyncio(run_func, options, cfg, run_once, t00)
        await trio_count()
    return rslt


def run(options, cfg, run_once, t00, run_func):
    print("running trio mode")
    instruments = []
    if cfg.get_plugin_param('trio.instrumenting', False):
        instruments.append(Tracer())
    rslt = trio.run(
        async_main_wrapper, options, cfg, run_once, t00, run_func,
        instruments=instruments,
        )
    dly, rslt_loop, notifiers = rslt
