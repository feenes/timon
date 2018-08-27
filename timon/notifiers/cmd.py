import os
import logging

from asyncio import subprocess
from asyncio import create_subprocess_exec
from asyncio import Semaphore  # move later to a central place for
#                                resource management

import timon.notifiers

top_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
script_dir = os.path.join(top_dir, "scripts", "notify")

logger = None
rsrc_sem = Semaphore(3)


class CmdNotifier(timon.notifiers.Notifier):
    def __init__(self, cmd, **kwargs):
        global logger
        logger = logger or logging.getLogger(__name__)

        super().__init__(**kwargs)

        basecmd = os.path.join(script_dir, cmd[0])
        args = cmd[1:]
        self.must_render_cmd = '{{' in ''.join(args)
        if self.must_render_cmd:
            from jinja2 import Template
            new_args = []
            for arg in args:
                if '{{' in arg:
                    arg = Template(arg)
                new_args.append(arg)
            args = new_args
        self.basecmd = basecmd
        self.args = args

    def create_final_command(self, probe, probe_state, user):
        final_cmd = [self.basecmd]
        if not self.must_render_cmd:
            final_cmd.extend(self.args)
        else:
            status = probe_state[-1][1]
            context = dict(vars(self))
            context.update(dict(
                status=status,
                user=user,
                probe=probe,
                probe_state=probe_state,
                ))
            logger.debug("ctx = %s", context)

            for arg in self.args:
                if hasattr(arg, 'render'):
                    final_cmd.append(arg.render(**context))
        return final_cmd

    async def notify(self, probe, probe_state):
        for user in self.users:
            async with rsrc_sem:
                final_cmd = self.create_final_command(probe, probe_state, user)
                logger.debug("call notify process")
                proc = await create_subprocess_exec(
                    *final_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    )
                stdout, stderr = await proc.communicate()
                logger.debug("notify process finished")
