#BitScope PiLab

An open source science lab for [Raspberry Pi](http://raspberrypi.org/) and [BitScope](http://bitscope.com/).

**[PiLab][4]** is an easy to use [open source programming platform](https://bitbucket.org/bitscope/pilab) written in [standard Python][6] for use with Raspberry Pi. It's designed to enable the creation of custom test, measurement and data acquisition applications in educational, engineering and scientific fields.  

PiLab uses a simple PNG graphical user interface that requires no complicated widget libraries and it has only few system prerequisites:

1. [Python 2.7][6] or later for PiLab programming,
2. [PyGame](http://www.pygame.org/) modules (for SDL based graphics), and
3. [PySerial](http://pyserial.sourceforge.net/) for USB access to the BitScope.

These are installed on Raspberry Pi as part of the default Raspbian distribution but PySerial may require upgrading to the latest version (using [pip](https://pypi.python.org/pypi/pip)) if you're running an older Raspbian release:

    $ sudo apt-get install python-pip
    $ sudo pip install pyserial --upgrade

Of course you'll also need a BitScope ([Micro][2] or [Model 10][1]) and a [Raspberry Pi][5] with a spare USB port capable of delivering 100mA of power.

##Quick Start

The PiLab code is *pure Python* so you simply need to run it *in situ*.

 1. Make sure your BitScope ([Model 10][1], or [Micro][2]) is connected.
 1. Change directory to the root folder of the respository in a terminal.
 1. In your terminal window type: **python main.py**

PiLab should start by opening a 1280x720 window with selection buttons down the left side to start one of the built-in PiLab applications. 

PiLab comes with a range of examples to get you started but you can create your own by cloning and modifying one of these and edit its JSON configuration files, PNG image files and (optionally) Python source to create custom applications of your own.

##BitScope Micro Test & Verify

What better example of PiLab than to use it to [test a BitScope][3]!

![BitScope Loop](http://bitscope.com/software/loop/01.gif)

Manufacture Q/A testing is vital to ensure a product works and meets its design specifications so we thought we'd use PiLab to build a highly optimised Q/A Test and Verification system to test the operation of [BitScope Micro][2] in production. 

Such an application needs to be reliable, easy to use and quick. Two of the example apps we've included in PiLab are the Q/A applications: **Test** and **Verify**. We use modified versions of these apps in the manufacture of BitScope Micro itself. They rely on a passive [test circuit][4] which you can build from a few resistors and capacitors. This circuit is quite handy for learning about BitScope in general because it feeds back the waveform and clock generators to BitScope's signal inputs so you need connect nothing else to explore all the features. We'll add more example applications soon and we encourage you to create your own!

##Project Information and Status

BitScope PiLab is a complete and operational platform but its documentation is in need of some love. The Python source is reasonably self-explanatory and the JSON files are easy to read and modify. Amending the Python source requires a detailed knowledge of the BitScope Virtual Machine (BVM). This is not hard but read the [BVM Programming Guide][4] and some [BVM Tutorials][4] first to learn how it works before trying to make wholesale changes to the Python source of a PiLab app (coming soon).

  [1]: http://bitscope.com/product/BS10/
  [2]: http://bitscope.com/micro/
  [3]: http://bitscope.com/software/loop/
  [4]: http://bitscope.com/soon/
  [5]: http://bitscope.com/blog/EK/?p=EK14H
  [6]: https://www.python.org/
