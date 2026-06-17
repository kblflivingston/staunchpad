"""The "agent" side: watch the job queue and dispatch each prompt, writing the
result back so the board can light up complete/error.

This is the seam where *your* always-on Claude Code agent lives. Three ways to
run it:

  --dry-run        pretend each job succeeds after a short delay (for testing LEDs)
  --cmd "TEMPLATE" run a shell command per job, e.g.
                     --cmd 'claude -p {prompt}'
                   (a non-zero exit marks the job as error)
  (no flag)        defaults to --dry-run

For the "always-on agent dispatches to a subagent" pattern you described, point a
persistent Claude Code session at this queue instead: have it watch the queue
directory and, for each new job, call the Agent/subagent tool with the prompt,
then mark the job done/error. The file protocol is documented in
staunchpad/dispatch.py.

    .venv/bin/python examples/dispatcher.py --dry-run
"""

import argparse
import subprocess
import time

from staunchpad.dispatch import JobQueue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", help="shell template run per job; {prompt} is substituted")
    ap.add_argument("--dry-run", action="store_true", help="simulate success")
    args = ap.parse_args()

    q = JobQueue()
    print(f"Dispatcher watching {q.dir}")
    print("mode:", "cmd: " + args.cmd if args.cmd else "dry-run")

    while True:
        for job in q.pending():
            if not q.claim(job):
                continue
            print(f"→ dispatching [{job.label or job.id}]: {job.prompt!r}")
            try:
                if args.cmd:
                    out = subprocess.run(args.cmd.format(prompt=job.prompt), shell=True,
                                         check=True, capture_output=True, text=True)
                    q.set_status(job.id, "done", result=out.stdout.strip()[:500])
                else:
                    time.sleep(1.5)                       # pretend work
                    q.set_status(job.id, "done", result="(dry-run ok)")
                print(f"  done [{job.label or job.id}]")
            except subprocess.CalledProcessError as e:
                q.set_status(job.id, "error", result=(e.stderr or str(e))[:500])
                print(f"  error [{job.label or job.id}]: {e}")
        time.sleep(0.3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
