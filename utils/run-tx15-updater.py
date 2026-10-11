"""Launch the dedicated updater. Opening a window never connects a device."""
import argparse
from usb_update.gui import main
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-report',help='Record disconnected window startup and exit; no connection')
    main(parser.parse_args().smoke_report)
