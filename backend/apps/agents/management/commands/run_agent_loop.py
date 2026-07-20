"""
Django 管理命令：运行 Agent 行为循环
===================================
用法：
  python manage.py run_agent_loop                # 对所有 Agent 执行一次循环
  python manage.py run_agent_loop --agent-id <id> # 对指定 Agent 执行一次
  python manage.py run_agent_loop --iterations 10 # 执行 10 次循环
"""
import time
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from backend.apps.agents.models import Agent
from backend.apps.agents.engine import GlobalEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "运行 Agent 行为循环（感知 规划 行动 记忆）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--agent-id", type=str,
            help="指定 Agent UUID，只运行该 Agent 的循环",
        )
        parser.add_argument(
            "--iterations", type=int, default=1,
            help="执行次数（默认 1 次）",
        )
        parser.add_argument(
            "--interval", type=float, default=0,
            help="循环间隔秒数（>0 时持续运行）",
        )

    def handle(self, *args, **options):
        agent_id = options.get("agent_id")
        iterations = options.get("iterations", 1)
        interval = options.get("interval", 0)

        engine = GlobalEngine()

        if agent_id:
            try:
                agent = Agent.objects.get(id=agent_id)
                agents = [agent]
            except Agent.DoesNotExist:
                raise CommandError(f"Agent with id '{agent_id}' not found")
        else:
            agents = list(
                Agent.objects.filter(status__in=["idle", "moving", "interacting"])
            )
            if not agents:
                self.stdout.write(self.style.WARNING("No active agents found"))
                return

        if interval > 0:
            self._run_continuous(engine, agents, interval)
        else:
            self._run_batch(engine, agents, iterations)

    def _run_batch(self, engine, agents, iterations):
        total_start = time.time()
        total_actions = 0

        for i in range(iterations):
            self.stdout.write(f"\n--- Iteration {i+1}/{iterations} ---")
            for agent in agents:
                try:
                    result = engine.run_single_iteration(agent)
                    self._log_result(result)
                    total_actions += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  [{agent.name}] Error: {e}")
                    )

        total_elapsed = time.time() - total_start
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {total_actions} actions across "
                f"{len(agents)} agents x {iterations} iterations "
                f"in {total_elapsed:.2f}s"
            )
        )

    def _run_continuous(self, engine, agents, interval):
        import signal
        import sys

        self.stdout.write(
            self.style.WARNING(
                f"Continuous loop for {len(agents)} agents "
                f"(interval={interval}s). Press Ctrl+C to stop."
            )
        )

        def signal_handler(sig, frame):
            engine.stop()
            self.stdout.write("\nStopped.")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        loop_count = 0

        try:
            while True:
                loop_count += 1
                start = time.time()
                self.stdout.write(f"\n--- Cycle #{loop_count} ---")

                for agent in agents:
                    try:
                        result = engine.run_single_iteration(agent)
                        self._log_result(result)
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  [{agent.name}] Error: {e}")
                        )

                elapsed = time.time() - start
                wait = max(0.5, interval - elapsed)
                self.stdout.write(
                    f"Cycle complete in {elapsed:.2f}s, next in {wait:.1f}s"
                )
                time.sleep(wait)
        except KeyboardInterrupt:
            engine.stop()
            self.stdout.write(self.style.SUCCESS("Stopped"))

    def _log_result(self, result):
        action_result = result.get("action_result", {})
        action_type = action_result.get("action_type", "?")
        description = action_result.get("description", "")[:60]
        success = action_result.get("success", False)
        memory_id = result.get("memory_id", "none")
        icon = "+" if success else "-"
        self.stdout.write(
            f"  {icon} [{result.get('agent_name','?')}] {action_type}: "
            f"{description}"
        )
