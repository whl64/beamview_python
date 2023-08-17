# Beamview
Beamview is a tool for viewing and analyzing camera images, built on [pyqtgraph](https://pyqtgraph.readthedocs.io/en/latest/) and [PyQt5](https://www.riverbankcomputing.com/software/pyqt/). Currently supports only Basler cameras via [pypylon](https://github.com/basler/pypylon) but is built to be extensible to other camera manufacturers.

Inspired by the original MATLAB Beamview used in the MEDUSA UED lab at Cornell.

Icons are from the the [2x upscaled Fugue icon set](https://github.com/chrisjbillington/fugue-2x-icons) by Chris Billington, originally created by [Yusuke Kamiyamane](https://p.yusukekamiyamane.com/). The Fugue icon set is licensed under a [creative-commons attribution license](http://creativecommons.org/licenses/by/3.0/), and may be used with [attribution](https://p.yusukekamiyamane.com/icon/attribution/) to the author. If you do not wish to provide attribution, you may [purchase a license](https://p.yusukekamiyamane.com/icon/license/).

# Features
* Realtime centroid/sigma calculations.
* Postprocessing including median filtering and thresholding.
* Simultaneous viewing of multiple cameras.
* Automatic bandwidth management.
* Variety of available colormaps.

# Prerequisites
* [pyqtgraph](https://pyqtgraph.readthedocs.io/en/latest/) >= 0.13.1
* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) >= 5.15.7
* [pypylon](https://github.com/basler/pypylon) >= 1.9.0
* [cmasher](https://cmasher.readthedocs.io/) >= 1.6.3
* [numpy](https://numpy.org/) >= 1.23.5
* [scipy](https://scipy.org/) >= 1.9.3

# Usage
All prerequisites are available on pip or conda. After installing all prerequisites, run beamview_python.py.

## Command line arguments
--debug: initialize 20 emulated cameras for testing 
