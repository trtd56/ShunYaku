from __future__ import annotations

import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.thread import _threads_queues, _worker


class DaemonThreadPoolExecutor(ThreadPoolExecutor):
    # Ctrl+C などでメインスレッドが終了したときに、ワーカーが残って
    # プロセスを保持し続けないよう daemon thread を使う。
    def _adjust_thread_count(self) -> None:
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(
            _,
            work_queue=self._work_queue,
        ) -> None:
            work_queue.put(None)

        num_threads = len(self._threads)
        if num_threads >= self._max_workers:
            return

        thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
        thread = threading.Thread(
            name=thread_name,
            target=_worker,
            args=(
                weakref.ref(self, weakref_cb),
                self._work_queue,
                self._initializer,
                self._initargs,
            ),
            daemon=True,
        )
        thread.start()
        self._threads.add(thread)
        _threads_queues[thread] = self._work_queue
