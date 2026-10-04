import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import chain_ram_session as s

class RecoveryScopeTests(unittest.TestCase):
    def test_backend_check_interrupt_is_deferred_until_ordinary_cleanup(self):
        import swd_flash
        import flash_transaction
        for error in (KeyboardInterrupt('cancel'),SystemExit('exit'),RuntimeError('USB read error')):
            report={'flash_info':{}}
            with patch.object(flash_transaction,'load_bundle',return_value=type('Plan',(),{'original_internal':b'I'*131072})()),\
                 patch.object(swd_flash,'read_only_check',side_effect=error):
                captured=s.capture_flash_backend_check(None,None,report,b'X'*64)
            self.assertIs(captured,error)
            self.assertIn('flash_backend_error',report)
            self.assertNotIn('flash_backend',report)

    def test_flash_reader_never_accesses_uninitialized_ltdc_or_adc_on_cleanup(self):
        # With PLL3 stopped, querying LTDC can leave this board's SWD in WAIT.
        def refuse(*args):raise AssertionError('Unowned application peripheral accessed')
        with patch.object(s.analog_session,'restore',side_effect=refuse),patch.object(s.display_session,'restore',side_effect=refuse):
            report={}
            s.restore_app_peripherals(lambda _:0,lambda *_:None,{}, {},report,flash_info_only=True)
            self.assertTrue(report['application_peripherals_untouched'])
            self.assertNotIn('restored_display',report)

    def test_application_cleanup_still_restores_its_adc_and_lcd(self):
        with patch.object(s.analog_session,'restore',return_value={'adc':True}) as a,patch.object(s.display_session,'restore',return_value=True) as d:
            report={};read=lambda _:0;write=lambda *_:None
            s.restore_app_peripherals(read,write,{}, {},report,flash_info_only=False)
            a.assert_called_once_with(read,write,{})
            d.assert_called_once_with(read,write,{})
            self.assertTrue(report['restored_display'])
