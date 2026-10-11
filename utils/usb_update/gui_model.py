"""GUI state separated from Tk and device access."""
from .client import UpdaterClient
from .package import unpack,HEADER_SIZE,MAX_IMAGE_SIZE
from pathlib import Path

class UpdaterModel:
    def __init__(self):
        self.info=None;self.package=None;self.raw=None;self.busy=False;self.success=False;self.finished=False
    @property
    def can_update(self):
        return bool(not self.busy and not self.finished and self.info and self.package
            and UpdaterClient._writable(self.info)
            and self.package.minimum_boot_api<=self.info.boot_api
            and self.package.settings_abi==self.info.settings_abi
            and len(self.package.image)<=self.info.max_image_bytes)
    def select_package(self,raw):
        self.package=None;self.raw=None;self.success=False
        package=unpack(raw);self.raw=bytes(raw);self.package=package
    def select_file(self,path):
        self.package=None;self.raw=None;self.success=False
        path=Path(path)
        if path.stat().st_size>HEADER_SIZE+MAX_IMAGE_SIZE:raise ValueError('固件文件过大')
        self.select_package(path.read_bytes())
    def connected(self,info):self.info=info;self.finished=False;self.success=False
    def disconnected(self):self.info=None;self.success=False
    def begin(self):
        if not self.can_update:raise RuntimeError('设备或固件尚未准备好')
        self.busy=True;self.success=False
    def complete(self,result):
        self.busy=False;self.finished=True
        self.success=bool(result.success and result.status and result.status.verified_done)
