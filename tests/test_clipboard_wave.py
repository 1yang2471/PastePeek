'''标准 Windows 音频剪贴板格式测试。'''

from src.clipboard import listener as listener_module


class WaveClipboard:
    '''只暴露 CF_WAVE 的最小 Win32 剪贴板接口。'''

    CF_UNICODETEXT = 13
    CF_DIB = 8
    CF_BITMAP = 2
    CF_HDROP = 15
    CF_WAVE = 12

    def OpenClipboard(self):
        pass

    def CloseClipboard(self):
        pass

    def RegisterClipboardFormat(self, _name):
        return 99

    def IsClipboardFormatAvailable(self, format_id):
        return format_id == self.CF_WAVE

    def GetClipboardData(self, format_id):
        raise AssertionError(f'未预期的数据读取：{format_id}')


def test_listener_detects_standard_cf_wave_as_binary(monkeypatch):
    '''标准音频格式必须沿公开读取接口标记为非文本。'''
    monkeypatch.setattr(listener_module, 'wc', WaveClipboard())

    data = listener_module.ClipboardListener().read()

    assert data.has_binary is True
