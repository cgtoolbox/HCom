# HCom
Hcom is a client – server communication system wrapped in a Pypanel in Houdini 14 ( 14.0.291 recommended ).
It allows users to send data from a Houdini session to another session throught local network.

You can send nodes or digital assets, even if the Houdini target client doesn't have access to that asset, Hcom will install it for you in your current session.
You can send also meshes as bgeo or obj format ( alembic coming soon … ) as well as image files.

To launch the server, you only need python 2.7.x and the rpyc library ( also shipped with Houdini ).
For the interface and the client side, everything you need ( PySide and rpyc ) is included in Houdini 14.x

INSTALL CLIENT:

Download the projet as zip file  ( https://github.com/GJpy/HCom/archive/master.zip )
Unzip the file in $HOME/houdini14.0/scripts/python or in any folder in your $PYTHONPATH
Rename the folder to "HCom"

Copy the HCom.pypanel file to your $HOME/houdini14.0/python_panels folder

Launch Houdini and add a python panel, clic on the cog-wheel icon and select "edit menu", and add HCom interface to your current menu, and that's it :)

LAUNCH SERVER:

With python 2.7.x installed on your machine with the rpyc python library ( you can find it in the HCom archive ), simple double-click on the HComServer.py, this will launch the server.
You can change the port used for the connection on the line 111 or the python file.

Demo on vimeo => https://vimeo.com/127091487

