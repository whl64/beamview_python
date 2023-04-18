# Beamview
Beamview is a tool for viewing and analyzing camera images, built on [pyqtgraph](https://pyqtgraph.readthedocs.io/en/latest/) and [PyQt5](https://www.riverbankcomputing.com/software/pyqt/). Currently supports only Basler cameras via [pypylon](https://github.com/basler/pypylon) but is built to be extensible to other camera manufacturers.

Inspired by the original MATLAB Beamview used in the MEDUSA UED lab at Cornell.

# Features
* Realtime centroid/sigma calculations
* Postprocessing including median filtering and thresholding
* Simultaneous viewing of multiple cameras.
* Automatic bandwidth management
* Variety of available colormaps 