import unittest
import sys
import types
from unittest.mock import patch
from assistant import classify, execute


class CommandsTest(unittest.TestCase):
    @patch('assistant.subprocess.Popen')
    def test_calculator(self, launch):
        execute('odpal kalkulator')
        launch.assert_called_once_with(['calc.exe'], shell=False)

    def test_latest(self):
        self.assertEqual(classify('odpal yt najnowszy odcinek @mkbhd'), ('latest', '@mkbhd'))

    @patch('assistant.webbrowser.open')
    def test_latest_opens_first_video_without_downloading(self, open_page):
        from unittest.mock import MagicMock
        ydl = MagicMock()
        ydl.return_value.__enter__.return_value.extract_info.return_value = {
            'entries': [{'id': 'abc123DEF_-', 'title': 'Najnowszy film'}]
        }
        module = types.ModuleType('yt_dlp')
        module.YoutubeDL = ydl
        with patch.dict(sys.modules, {'yt_dlp': module}):
            result = execute('odpal yt najnowszy odcinek @mkbhd')
        ydl.return_value.__enter__.return_value.extract_info.assert_called_once_with(
            'https://www.youtube.com/@mkbhd/videos', download=False)
        open_page.assert_called_once_with('https://www.youtube.com/watch?v=abc123DEF_-')
        self.assertIn('Najnowszy film', result)

    @patch('assistant.subprocess.Popen')
    def test_arbitrary_command_rejected(self, launch):
        execute('powershell Remove-Item C:')
        launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()