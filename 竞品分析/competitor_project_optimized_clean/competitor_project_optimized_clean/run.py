"""
北美伴娘服竞品监控雷达 - 统一多线程调度中心（懒加载兼容版）

使用方法:
  python run.py --site az          # 只跑 Azazie
  python run.py --site bg          # 只跑 Birdy Grey
  python run.py --site ss          # 只跑 Six Stories
  python run.py --site cl          # 只跑 Club L London
  python run.py --site bb          # 只跑 Babyboo Fashion
  python run.py --site hm          # 只跑 Hello Molly
  python run.py --site all         # 并发跑全部网站，GLOBAL_SITE_WORKERS 控制并发数
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from dotenv import load_dotenv


@dataclass(frozen=True)
class SiteTaskSpec:
    site_key: str
    site_name: str
    module_name: str
    function_name: str


SITE_TASK_SPECS: dict[str, SiteTaskSpec] = {
    "az": SiteTaskSpec("az", "Azazie", "main_az", "run_az"),
    "bg": SiteTaskSpec("bg", "Birdy Grey", "main_bg", "run_bg"),
    "ss": SiteTaskSpec("ss", "Six Stories", "main_ss", "run_ss"),
    "cl": SiteTaskSpec("cl", "Club L London", "main_cl", "run_cl"),
    "bb": SiteTaskSpec("bb", "Babyboo Fashion", "main_bb", "run_bb"),
    "hm": SiteTaskSpec("hm", "Hello Molly", "main_hm", "run_hm"),
}


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _setup_logging() -> None:
    # 必须在导入各站点模块之前加载 .env，避免各 main_xxx.py 在 import 阶段读取不到配置。
    load_dotenv(override=True)

    log_level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
    )


_setup_logging()
logger = logging.getLogger("Scheduler")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="多线程电商竞品监控雷达")

    parser.add_argument(
        "--site",
        choices=["az", "bg", "ss", "cl", "bb", "hm", "all"],
        default="all",
        help=(
            "选择要抓取的站点: "
            "az(Azazie), bg(Birdy Grey), ss(Six Stories), "
            "cl(Club L London), bb(Babyboo Fashion), hm(Hello Molly), all(全部并发)"
        ),
    )


    return parser.parse_args()


def _get_selected_specs(site: str) -> list[SiteTaskSpec]:
    if site == "all":
        order = os.getenv("GLOBAL_SITE_ORDER", "az,bg,ss,cl,bb,hm")
        ordered_keys = [item.strip().lower() for item in order.split(",") if item.strip()]

        specs: list[SiteTaskSpec] = []
        seen: set[str] = set()
        for key in ordered_keys:
            spec = SITE_TASK_SPECS.get(key)
            if spec and key not in seen:
                specs.append(spec)
                seen.add(key)

        for key, spec in SITE_TASK_SPECS.items():
            if key not in seen:
                specs.append(spec)

        return specs

    return [SITE_TASK_SPECS[site]]


def _load_runner(spec: SiteTaskSpec) -> Callable[[], None]:
    """
    懒加载站点模块。

    这样只跑单站时，不会因为其他站点 main_xxx.py 暂时有语法/依赖问题而导致 run.py 启动失败。
    """
    module = importlib.import_module(spec.module_name)
    runner = getattr(module, spec.function_name)
    if not callable(runner):
        raise TypeError(f"{spec.module_name}.{spec.function_name} 不是可调用函数")
    return runner


def _get_global_workers(task_count: int) -> int:
    try:
        configured_workers = int(os.getenv("GLOBAL_SITE_WORKERS", "2") or "2")
    except ValueError:
        configured_workers = 2

    configured_workers = max(1, configured_workers)
    return min(task_count, configured_workers)


def main() -> None:
    args = parse_args()

    logger.info(
        "🚀 监控雷达启动 | 目标站点: %s",
        args.site.upper(),
    )

    start_time = time.time()
    selected_specs = _get_selected_specs(args.site)

    if not selected_specs:
        logger.warning("没有可执行任务，请检查 --site 参数")
        return

    task_map: dict[str, Callable[[], None]] = {}
    import_failures: list[str] = []

    for spec in selected_specs:
        try:
            task_map[spec.site_name] = _load_runner(spec)
        except Exception as exc:
            import_failures.append(spec.site_name)
            logger.exception(
                "❌ %s 模块加载失败: %s.%s | %s",
                spec.site_name,
                spec.module_name,
                spec.function_name,
                exc,
            )

    if not task_map:
        elapsed = time.time() - start_time
        logger.error("没有任何站点成功加载，流程结束 | 总耗时 %.2f 秒", elapsed)
        return

    max_workers = _get_global_workers(len(task_map))

    logger.info(
        "任务并发数: %s | 可通过 GLOBAL_SITE_WORKERS 调整 | 已加载站点=%s",
        max_workers,
        ", ".join(task_map.keys()),
    )

    failures: list[str] = []

    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="Spider",
    ) as executor:
        futures = {
            executor.submit(func): site_name
            for site_name, func in task_map.items()
        }

        for future in as_completed(futures):
            site_name = futures[future]

            try:
                future.result()
                logger.info("✅ %s 任务完成", site_name)
            except Exception as exc:
                failures.append(site_name)
                logger.exception("❌ %s 任务抛出未捕获异常: %s", site_name, exc)

    elapsed = time.time() - start_time
    all_failures = import_failures + failures

    if all_failures:
        logger.error(
            "⚠️ 部分任务失败: %s | 总耗时 %.2f 秒",
            ", ".join(all_failures),
            elapsed,
        )
    else:
        logger.info("🎉 全部任务执行完毕！总耗时: %.2f 秒", elapsed)


if __name__ == "__main__":
    main()
