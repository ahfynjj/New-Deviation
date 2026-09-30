# Integration build only: deliberately no DFU/Flash artifact.
SCREENSIZE := 320x240x16
ALL := tx15-integration
.PHONY: tx15-integration
tx15-integration:
	python ../utils/build-tx15-app.py
