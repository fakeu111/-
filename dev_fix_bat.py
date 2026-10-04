"""把 build.bat 转成 GBK + CRLF，保证 cmd 下中文正常。"""
from pathlib import Path

p = Path(__file__).parent / "build.bat"
text = p.read_text(encoding="utf-8")
text = text.replace("\r\n", "\n").replace("\n", "\r\n")
p.write_bytes(text.encode("gbk"))
print("converted", p)
