"""pytest 全局配置：在导入 Qt 前设置离屏平台，并隔离测试数据库。"""
import os
import pathlib
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 让测试使用独立的临时数据库，不污染真实数据
_test_db = pathlib.Path(tempfile.mkdtemp()) / "test_studydesk.db"
os.environ["STUDYDESK_DB"] = str(_test_db)
